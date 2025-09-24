import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector

from dictionary import DIRECTIONS, CITIES_TO_TASHKENT, CITIES_FROM_TASHKENT, SEAT_OPTIONS, REQUEST_A_RIDE, phone_number_regEx, INVALID_COMMAND
from database.Mysql import Mysql
from config import DB_CONFIG
from modules import helper

passenger_router = Router()

# ----- States -----
class PassengerForm(StatesGroup):
	direction = State()
	route = State()
	seats = State()
	phone = State()

# --- Route Start ---
@passenger_router.message(F.text == REQUEST_A_RIDE)
async def start_passenger_flow(message: Message, state: FSMContext):
	await state.set_state(PassengerForm.direction)
	await message.answer("🗺 Yo‘nalishni tanlang:", reply_markup=helper.build_kb(DIRECTIONS, per_row=2))


@passenger_router.message(PassengerForm.direction)
async def handle_direction(message: Message, state: FSMContext):
	direction = message.text.strip()
	if direction not in DIRECTIONS:
		await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb(DIRECTIONS, per_row=2), parse_mode="HTML")
		return

	await state.update_data(direction=direction)
	if direction == "🚖 Viloyatdan → Toshkentga":
		await state.set_state(PassengerForm.route)
		await message.answer("Kerakli yo'nalishni tanlang 👇", reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2))

	elif direction == "🚖 Toshkentdan → Viloyatga":
		await state.set_state(PassengerForm.route)
		await message.answer("Kerakli yo'nalishni tanlang 👇", reply_markup=helper.build_kb(CITIES_FROM_TASHKENT, per_row=2))


@passenger_router.message(PassengerForm.route)
async def handle_from_city(message: Message, state: FSMContext):
	selected_route = message.text.strip()
	data = await state.get_data()
	direction = data.get("direction")

	if direction == "🚖 Viloyatdan → Toshkentga":
		if selected_route not in CITIES_TO_TASHKENT:
			await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2), parse_mode="HTML")
			return

	elif direction == "🚖 Toshkentdan → Viloyatga":
		if selected_route not in CITIES_FROM_TASHKENT:
			await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb(CITIES_FROM_TASHKENT, per_row=2), parse_mode="HTML")
			return

	# Split into from/to cities
	from_city, to_city = selected_route.split(" → ")
	await state.update_data(from_city=from_city, to_city=to_city)

	await state.set_state(PassengerForm.seats)
	await message.answer("💺 Iltimos yo'lovchi sonini tanlang 👇", reply_markup=helper.build_kb(SEAT_OPTIONS, per_row=2))


@passenger_router.message(PassengerForm.seats)
async def handle_seats(message: Message, state: FSMContext):
	text = message.text.strip()
	try: seat = int(text)
	except ValueError:
		await message.answer(INVALID_COMMAND, reply_markup=helper.build_kb(SEAT_OPTIONS, per_row=2), parse_mode="HTML")
		return

	if seat not in SEAT_OPTIONS:
		await message.answer("❌ Yo'lovchilar soni noto'g'ri. Iltimos, menyudan tanlang 👇", reply_markup=helper.build_kb(SEAT_OPTIONS, per_row=2))
		return

	await state.update_data(seats=seat)

	# Get previously stored from/to cities
	data = await state.get_data()
	from_city = data.get("from_city")
	to_city = data.get("to_city")

	# Ask for phone number
	await state.set_state(PassengerForm.phone)
	await message.answer(
		f"🚖 {from_city} → {to_city} yo‘nalishi\n\n"
		f"📞 Buyurtma uchun telefon raqamingizni to‘liq yuboring:\n\n"
		"❗️ Namuna: +998901234567",
		reply_markup=helper.cancel_request_kb()
	)


@passenger_router.message(PassengerForm.phone)
async def handle_phone(message: Message, state: FSMContext):
	phone = message.text.strip()

	# Phone number regex: (+9989901234567)
	if not re.match(phone_number_regEx, phone):
		await message.answer("❌ Telefon formati noto‘g‘ri. Namuna: +998901234567")
		return

	await state.update_data(phone=phone)
	data = await state.get_data()

	# Get passenger id
	passenger_id = Mysql.execute(
		sql="""
			INSERT INTO users (telegram_id, name, phone)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				name = VALUES(name),
				phone = VALUES(phone),
				id = LAST_INSERT_ID(id)
		""",
		params=[
			message.from_user.id,
			message.from_user.full_name,
			phone
		],
		commit=True
	)

	# Save passenger ride
	request_id = Mysql.execute(
		sql="""
			INSERT INTO ride_requests
			(
				passenger_id,
				from_city,
				to_city,
				passenger_name,
				passenger_phone,
				seats,
				status
			)
			VALUES (%s, %s, %s, %s, %s, %s, 'pending')
		""",
		params=[
			passenger_id,
			data["from_city"],
			data["to_city"],
			message.from_user.full_name,
			data["phone"],
			data["seats"]
		],
		commit=True
	)

	# Fetch drivers
	drivers = Mysql.execute(
		sql="""
			SELECT
				drivers.id,
				users.telegram_id,
				users.name
			FROM drivers
			JOIN users ON users.id = drivers.user_id
			WHERE
				drivers.from_city=%s AND
				drivers.to_city=%s AND
				is_contract_signed IS TRUE
		""",
		params=[data["from_city"], data["to_city"]],
		fetchall=True
	)

	# Notify all drivers with new request and insert into ride_notifications
	for driver in drivers:
		try:
			Mysql.execute(
				sql="""
					INSERT INTO ride_notifications (ride_id, driver_id)
					VALUES (%s, %s)
					ON DUPLICATE KEY UPDATE notified_at=NOW()
				""",
				params=[request_id, driver["id"]],
				commit=True
			)

			await message.bot.send_message(
				driver["telegram_id"],
				f"✨ Yangi so'rov!\n\n"
				f"🧑‍💼 Yo'lovchi: {message.from_user.full_name}\n"
				f"📍 Yo'nalish: {data["from_city"]} → {data["to_city"]}\n"
				f"💺 O'rindiqlar: {data["seats"]}\n\n"
				f"🚀 Safarga tayyormisiz? So'rovni qabul qiling!",
				reply_markup=helper.driver_accept_kb(request_id)
			)
		except Exception as e: print(f"⚠️ Could not notify {driver['name']}: {e}")

	# Notify passenger
	await message.answer(
		"✅ Buyurtma qabul qilindi.\n\n"
		"⏳Tez orada haydovchi siz bilan bog'lanadi.",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()
