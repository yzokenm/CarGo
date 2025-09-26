import re

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from modules import helper
from database.Mysql import Mysql

# Lang set up
from language import Lang

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	terms_and_conditions = State()
	route = State()
	phone = State()

# --- Route Start ---
@driver_router.message(F.text == Lang.use("register_driver"))
async def start_driver_flow(message: Message, state: FSMContext):
	await state.set_state(DriverForm.terms_and_conditions)
	await message.answer(Lang.use("terms_and_conditions_msg"), reply_markup=helper.build_kb([Lang.use("terms_and_conditions")], per_row=2), parse_mode="HTML")

@driver_router.message(DriverForm.terms_and_conditions)
async def handle_terms(message: Message, state: FSMContext):
	if message.text.strip() == Lang.use("terms_and_conditions"):
		await state.update_data(is_contract_signed=True)
		await state.set_state(DriverForm.route)
		await message.answer("🗺 Iltimos, faoliyat yuritadigan shahringizni tanlang:", reply_markup=helper.build_kb(Lang.use("cities_to_tashkent"), per_row=2))
	else: await message.answer(Lang.use("invalid_command"), reply_markup=helper.build_kb([Lang.use("terms_and_conditions")], per_row=2), parse_mode="HTML")

@driver_router.message(DriverForm.route)
async def handle_route(message: Message, state: FSMContext):
	selected_route = message.text.strip()
	if selected_route not in Lang.use("cities_to_tashkent"):
		await message.answer(Lang.use("invalid_command"), reply_markup=helper.build_kb(Lang.use("cities_to_tashkent"), per_row=2), parse_mode="HTML")
		await state.set_state(DriverForm.route)
		return

	# Split into from/to cities
	from_city, to_city = selected_route.split(" → ")
	await state.update_data(from_city=from_city, to_city=to_city)

	# Ask for phone number
	await state.set_state(DriverForm.phone)
	await message.answer(
		f"🚖 {from_city} → {to_city} yo'nalishi\n\n"
		f"📞 Ro'yxatdan o'tish uchun telefon raqamingizni to'liq yuboring:\n\n"
		"❗️ Namuna: +998901234567",
		reply_markup=helper.cancel_request_kb()
	)

@driver_router.message(DriverForm.phone)
async def handle_phone(message: Message, state: FSMContext):
	phone = message.text.strip()

	if not re.match(Lang.use("phone_regex"), phone):
		await message.answer("❌ Telefon formati noto'g'i. Namuna: +998901234567")
		return

	await state.update_data(phone=phone)
	data = await state.get_data()

	# Save driver
	result = helper.save_driver(
		telegram_id=message.from_user.id,
		name=message.from_user.full_name,
		phone=phone,
		from_city=data["from_city"],
		to_city=data["to_city"],
		is_contract_signed=data["is_contract_signed"]
	)

	# Check if driver already registered
	if result == "driver_exist":
		await message.answer("🚖 Siz ro'yxatdan o'tib bo'lgansiz!\n\n ❗Takroriy ro'yxatdan o'tish talab qilinmaydi.")
		return
	else:
		await message.answer(
				f"🎉 Tabriklaymiz! Siz haydovchi sifatida ro'yxatdan o'tdingiz.\n\n"
				f"📋 Sizning ma'lumotlaringiz:\n"
				f"👤 Ism: {message.from_user.full_name}\n"
				f"📞 Telefon: {phone}\n"
				f"🏙 Qatnov yo'nalish: {data['from_city']} → {data['to_city']}\n\n"
				f"⏳ Tez orada sizga yangi so'rovlar keladi. Safarga tayyor turing!",
			reply_markup=ReplyKeyboardRemove()
		)
	await state.clear()

# ---- Accept order ----
@driver_router.callback_query(F.data.startswith("accept:"))
async def handle_accept_order(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	driver_telegram_id = callback.from_user.id

	# Get driver Info
	driver = Mysql.execute(
		sql="""
			SELECT
				drivers.id,
				drivers.from_city,
				drivers.to_city,
				users.name,
				users.phone
			FROM drivers
			JOIN users ON users.id = drivers.user_id
			WHERE users.telegram_id=%s
		""",
		params=[driver_telegram_id],
		fetchone=True
	)

	if driver: driver_id = driver["id"]
	else:
		await callback.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
		return

	# Accept ride if still pending
	affected_rows = Mysql.execute(
		sql="""
			UPDATE ride_requests
			SET
				status='taken',
				taken_by_driver_id=%s
			WHERE
				id=%s AND
				status='pending'
		""",
		params=(driver_id, request_id),
		commit=True,
		return_rowcount=True
	)

	# Send notif when ride was already taken
	if affected_rows == 0:
		await callback.answer("⚠️ Ushbu buyurtma boshqa haydovchi tomonidan qabul qilindi. ⏳ Yangi so'rovni kutishingiz mumkin.", show_alert=True)
		return

	# Get passenger ride details
	ride = Mysql.execute(
		sql="""
			SELECT
				ride_requests.passenger_name,
				ride_requests.passenger_phone,
				ride_requests.from_city,
				ride_requests.to_city,
				ride_requests.seats,
				users.telegram_id AS passenger_telegram_id
			FROM ride_requests
			JOIN users ON ride_requests.passenger_id = users.id
			WHERE ride_requests.id=%s
		""",
		params=[request_id],
		fetchone=True
	)

	# Insert into ride_notifications
	Mysql.execute(
		sql="""
			INSERT INTO ride_notifications (ride_id, driver_id)
			VALUES (%s, %s)
			ON DUPLICATE KEY UPDATE notified_at=NOW()
		""",
		params=[request_id, driver_id],
		commit=True
	)

	# Notify driver
	await callback.message.edit_reply_markup()
	await callback.message.answer(
		f"🎉 So'rov qabul qilindi!\n\n"
		f"🧑‍💼 Yo'lovchi: {ride['passenger_name']}\n"
		f"☎️ Telefon: {ride['passenger_phone']}\n"
		f"📍 Yo'nalish: {ride['from_city']} → {ride['to_city']}\n"
		f"💺 Kerakli o'rindiqlar: {ride['seats']}\n\n"
		"🤝 Iltimos, yo'lovchi bilan bog'laning!"
	)

	# Notify passenger with cancel option
	await callback.bot.send_message(
		chat_id=ride['passenger_telegram_id'],
		text=(
			f"✅ Haydovchi so'rovingizni qabul qildi!\n\n"
			f"👨‍✈️ Haydovchi: {driver["name"]}\n"
			f"📞 Telefon: {driver["phone"]}\n\n"
			"📲 Haydovchi bilan bog'lanishingiz mumkin.\n"
			"❌ Agar haydovchi bilan kelisha olmasangiz, <b>Bekor qilish</b> tugmasini bosing va boshqa haydovchini kutishingiz mumkin."
		),
		reply_markup=helper.cancel_driver_kb(request_id),
		parse_mode="HTML"
	)

# ---- Cancel driver (passenger action) ----
@driver_router.callback_query(F.data.startswith("cancel_driver:"))
async def handle_cancel_driver(callback: CallbackQuery):
	request_id = int(callback.data.split(":")[1])
	cancelled_driver_telegram = None

	# Get cancelled driver
	cancelled_driver = Mysql.execute(
		sql="""
			SELECT
				ride_requests.taken_by_driver_id AS id,
				users.telegram_id
			FROM ride_requests
			JOIN drivers ON drivers.id = ride_requests.taken_by_driver_id
			JOIN users ON users.id = drivers.user_id
			WHERE
				ride_requests.id=%s AND
				ride_requests.status='taken'
		""",
		params=[request_id],
		fetchone=True
	)
	cancelled_driver_id = cancelled_driver["id"] if cancelled_driver else None
	cancelled_driver_telegram = cancelled_driver["telegram_id"] if cancelled_driver else None

	# Reset ride
	Mysql.execute(
		sql="""
			UPDATE ride_requests
			SET
				status='pending',
				taken_by_driver_id=NULL
			WHERE
				id=%s AND
				status='taken'
		""",
		params=[request_id],
		commit=True
	)

	# Delete all old notifications for this ride
	Mysql.execute(
		sql="DELETE FROM ride_notifications WHERE ride_id=%s",
		params=[request_id],
		commit=True
	)

	# Fetch ride
	ride = Mysql.execute(
		sql="""
			SELECT
				ride_requests.id,
				ride_requests.passenger_name,
				ride_requests.passenger_phone,
				ride_requests.from_city,
				ride_requests.to_city,
				ride_requests.seats,
				users.telegram_id AS passenger_telegram_id
			FROM ride_requests
			JOIN users ON users.id = ride_requests.passenger_id
			WHERE ride_requests.id=%s
		""",
		params=[request_id],
		fetchone=True
	)

	# Get all drivers (optional: exclude cancelled driver)
	if cancelled_driver_id:
		drivers = Mysql.execute(
			sql="""
				SELECT
					drivers.id,
					users.telegram_id
				FROM drivers
				JOIN users ON users.id = drivers.user_id
				WHERE drivers.id != %s
			""",
			params=[cancelled_driver_id],
			fetchall=True
		)
	else:
		drivers = Mysql.execute(
			sql="""
				SELECT
					drivers.id,
					users.telegram_id
				FROM drivers
				JOIN users ON users.id = drivers.user_id
			""",
			fetchall=True
		)

	# Notify passenger
	await callback.message.edit_text("❌ Siz haydovchini bekor qildingiz.\n\n 🔄 So'rovingiz qayta faollashtirildi. \n\n ⏳ Boshqa haydovchilar tez orada sizga aloqaga chiqishadi.")

	# Notify cancelled driver
	if cancelled_driver_telegram:
		try:
			await callback.bot.send_message(
				chat_id=cancelled_driver_telegram,
				text="⚠️ Yo‘lovchi so'rovni bekor qildi. \n\n ⏳ So'rov qayta faollashtirildi."
			)
		except: pass

	# Re-send ride to all available drivers
	for driver in drivers:
		try:
			await callback.bot.send_message(
				driver["telegram_id"],
				f"🚕 Yangi so'rov!\n"
				f"👤 Yo'lovchi: {ride['passenger_name']}\n"
				f"📍 Yo'nalish: {ride['from_city']} → {ride['to_city']}\n"
				f"💺 Kerakli o'rindiqlar: {ride['seats']}\n",
				reply_markup=helper.driver_accept_kb(ride['id'])
			)

			Mysql.execute(
				sql="INSERT INTO ride_notifications (ride_id, driver_id) VALUES (%s, %s)",
				params=[ride['id'], driver['id']],
				commit=True
			)
		except Exception as e: print(f"⚠️ Could not notify driver {driver['id']}: {e}")
