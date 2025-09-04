from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import mysql.connector
from database.config import DB_CONFIG, CITIES, SEAT_OPTIONS, TIME_OPTIONS
from database.db import get_connection
import re
from handlers import helper

passenger_router = Router()

class PassengerForm(StatesGroup):
	from_city = State()
	to_city = State()
	date = State()
	seats = State()
	phone = State()

# --- DB Helpers ---
def ensure_user_and_get_id(telegram_id, name, phone):
	conn = get_connection()
	cur = conn.cursor()
	cur.execute("""
		INSERT INTO users (telegram_id, role, name, phone_number)
		VALUES (%s, 'passenger', %s, %s)
		ON DUPLICATE KEY UPDATE role=VALUES(role), name=VALUES(name), phone_number=VALUES(phone_number)
	""", (telegram_id, name, phone))
	conn.commit()
	cur.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
	user_id = cur.fetchone()[0]
	cur.close()
	conn.close()
	return user_id

def insert_request(passenger_id, from_city, to_city, date_iso, seats, passenger_name, passenger_phone):
	conn = get_connection()
	cur = conn.cursor()
	cur.execute("""
		INSERT INTO ride_requests
		(passenger_id, from_city, to_city, date, seats, passenger_name, passenger_phone, status)
		VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
	""", (passenger_id, from_city, to_city, date_iso, seats, passenger_name, passenger_phone))
	conn.commit()
	request_id = cur.lastrowid
	cur.close()
	conn.close()
	return request_id


# --- Flow ---
@passenger_router.message(F.text == "🚖 Taksi buyurtma berish")
async def start_passenger_flow(message: Message, state: FSMContext):
	await state.set_state(PassengerForm.from_city)
	kb = helper.build_kb(CITIES, exclude="Shaxrixon", per_row=2)
	await message.answer("Ketish shahrini tanlang:", reply_markup=kb)

@passenger_router.message(PassengerForm.from_city)
async def handle_from_city(message: Message, state: FSMContext):
	city = message.text.strip()
	if city not in CITIES:
		kb = helper.build_kb(CITIES, per_row=2)
		await message.answer("Iltimos menyudagi shaharni tanlang:", reply_markup=kb)
		return

	await state.update_data(from_city=city)
	await state.set_state(PassengerForm.to_city)
	kb = helper.build_kb(CITIES, exclude=city, per_row=2)
	await message.answer("Yetib borish shaxrini tanlang:", reply_markup=kb)

@passenger_router.message(PassengerForm.to_city)
async def handle_to_city(message: Message, state: FSMContext):
	data = await state.get_data()
	from_city = data.get("from_city")
	dest = message.text.strip()
	if dest not in CITIES or dest == from_city:
		kb = helper.build_kb(CITIES, exclude=from_city, per_row=2)
		await message.answer("Iltimos boshqa shaxarni tanlang:", reply_markup=kb)
		return
	await state.update_data(to_city=dest)
	await state.set_state(PassengerForm.date)
	DATE_OPTIONS = helper.get_date_options(days=3)
	kb = helper.build_kb(DATE_OPTIONS, per_row=2)
	await message.answer("Sayohat sanasini tanlang:", reply_markup=kb)

@passenger_router.message(PassengerForm.date)
async def handle_date(message: Message, state: FSMContext):
	raw = message.text.strip()

	# Try to extract date inside parentheses
	match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", raw)
	if not match:
		DATE_OPTIONS = helper.get_date_options(days=3)
		kb = helper.build_kb(DATE_OPTIONS, per_row=2)
		await message.answer("Iltimos, menyudagi sanani tanlang:", reply_markup=kb)
		return

	dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
	today = datetime.now().date()

	if not (today <= dt <= today + timedelta(days=2)):
		DATE_OPTIONS = helper.get_date_options(days=3)
		kb = helper.build_kb(DATE_OPTIONS, per_row=2)
		await message.answer("Iltimos, ko'rsatilgan sanalardan birini tanlang:", reply_markup=kb)
		return

	await state.update_data(date=dt.strftime("%Y-%m-%d"))
	await state.set_state(PassengerForm.seats)
	kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
	await message.answer("O'rindiqlar soni:", reply_markup=kb)

@passenger_router.message(PassengerForm.seats)
async def handle_seats(message: Message, state: FSMContext):
	txt = message.text.strip()
	if not txt.isdigit() or int(txt) not in SEAT_OPTIONS:
		kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
		await message.answer("Iltimos, menyudan tanlang:", reply_markup=kb)
		return

	await state.update_data(seats=int(txt))

	# Ask for phone number
	await state.set_state(PassengerForm.phone)
	await message.answer(
		"📱 Telefon raqamingizni kiriting (format: +998901234567):",
		reply_markup=ReplyKeyboardRemove()
	)

@passenger_router.message(PassengerForm.phone)
async def handle_phone(message: Message, state: FSMContext):
	phone = message.text.strip()

	# Validate Uzbek phone format (simple check)
	if not re.match(r"^\+?998\d{9}$", phone):
		await message.answer("❌ Telefon formati noto‘g‘ri. Misol: +998901234567")
		return

	await state.update_data(phone=phone)

	data = await state.get_data()
	from_city = data["from_city"]
	to_city = data["to_city"]
	date = data["date"]
	seats = data["seats"]
	phone = data["phone"]

	# Save passenger + request
	try:
		passenger_id = ensure_user_and_get_id(message.from_user.id, message.from_user.full_name, phone)
		request_id = insert_request(
			passenger_id,
			from_city,
			to_city,
			date,
			seats,
			message.from_user.full_name,
			phone
		)

		# Get all registered drivers
		conn = get_connection()
		cur = conn.cursor(dictionary=True)
		cur.execute("SELECT telegram_id, name FROM users WHERE role='driver'")
		drivers = cur.fetchall()
		cur.close()
		conn.close()

	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e}")
		await state.clear()
		return

	# Send request details to each driver
	for d in drivers:
		try:
			await message.bot.send_message(
				d["telegram_id"],
				f"🚕 Yangi so'rov!\n"
				f"👤 Yo'lovchi: {message.from_user.full_name}\n"
				f"📍 {from_city} → {to_city}\n"
				f"📅 Sana: {date}\n"
				f"💺 O'rindiqlar: {seats}\n"
				f"☎️ Telefon: {phone}\n",
				reply_markup=helper.driver_accept_kb(request_id)
			)
		except Exception:
			# ignore errors if driver blocked the bot
			pass

	# Notify passenger
	await message.answer(
		"✅ So'rovingiz qabul qilindi.\n"
		"☎️ Tez orada haydovchi siz bilan bog'lanadi.",
		reply_markup=ReplyKeyboardRemove()
	)

	await state.clear()


