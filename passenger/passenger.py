import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import mysql.connector

from database.config import DB_CONFIG, DIRECTIONS, CITIES_TO_TASHKENT, CITIES_FROM_TASHKENT, SEAT_OPTIONS
from database.db import get_connection
from modules import helper

passenger_router = Router()

# ----- States -----
class PassengerForm(StatesGroup):
	direction = State()
	route = State()
	seats = State()
	phone = State()

# --- Flow ---
@passenger_router.message(F.text == "🚖 Taksi buyurtma berish")
async def start_passenger_flow(message: Message, state: FSMContext):
	await state.set_state(PassengerForm.direction)
	kb = helper.build_kb(DIRECTIONS, per_row=2)
	await message.answer("Yo‘nalishni tanlang:", reply_markup=kb)


@passenger_router.message(PassengerForm.direction)
async def handle_direction(message: Message, state: FSMContext):
	direction = message.text.strip()

	if direction not in DIRECTIONS:
		await message.answer(
			"❌ Noto‘g‘ri tanlov. Iltimos, menyudan tanlang:",
			reply_markup=helper.build_kb(DIRECTIONS, per_row=1)
		)
		return

	await state.update_data(direction=direction)

	if direction == "🚖 Viloyatdan → Toshkentga":
		await state.set_state(PassengerForm.route)
		await message.answer(
			"Qaysi shaxardan Toshkentga ketasiz?",
			reply_markup=helper.build_kb(CITIES_TO_TASHKENT, per_row=2)
		)

	elif direction == "🚖 Toshkentdan → Viloyatga":
		await state.set_state(PassengerForm.route)
		await message.answer(
			"Toshkentdan qaysi shaxarga ketasiz?",
			reply_markup=helper.build_kb(CITIES_FROM_TASHKENT, per_row=2)
		)


@passenger_router.message(PassengerForm.route)
async def handle_from_city(message: Message, state: FSMContext):
	route = message.text.strip()

	if route not in (CITIES_TO_TASHKENT + CITIES_FROM_TASHKENT):
		await message.answer(
			"❌ Noto‘g‘ri yo‘nalish. Iltimos, menyudan tanlang:",
			reply_markup=helper.build_kb(CITIES_TO_TASHKENT + CITIES_FROM_TASHKENT, per_row=2)
		)
		return

	# Split into from/to cities
	from_city, to_city = route.split(" → ")
	await state.update_data(from_city=from_city, to_city=to_city)

	await state.set_state(PassengerForm.seats)
	kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
	await message.answer("O'rindiqlar soni:", reply_markup=kb)


@passenger_router.message(PassengerForm.seats)
async def handle_seats(message: Message, state: FSMContext):
	seat = int(message.text.strip())
	if seat not in SEAT_OPTIONS:
		kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
		await message.answer("Iltimos, menyudan tanlang:", reply_markup=kb)
		return

	await state.update_data(seats=seat)

	# Ask for phone number
	await state.set_state(PassengerForm.phone)
	await message.answer(
		"📱 Telefon raqamingizni kiriting (format: +998901234567):",
		reply_markup=ReplyKeyboardRemove()
	)


@passenger_router.message(PassengerForm.phone)
async def handle_phone(message: Message, state: FSMContext):
	phone = message.text.strip()

	# Check if phone_number valid(+9989901234567)
	if not re.match(r"^\+?998\d{9}$", phone):
		await message.answer("❌ Telefon formati noto‘g‘ri. Misol: +998901234567")
		return

	await state.update_data(phone=phone)
	data = await state.get_data()

	try:
		# Get passenger id
		passenger_id = helper.save_passenger(message.from_user.id, message.from_user.full_name, phone)

		# Save passenger ride
		request_id = helper.save_passenger_ride(
			passenger_id,
			message.from_user.full_name,
			data["from_city"],
			data["to_city"],
			data["seats"],
			data["phone"]
		)

		# Fetch drivers
		conn = get_connection()
		cur = conn.cursor(dictionary=True)

		cur.execute(
			"""
				SELECT id, telegram_id, name
				FROM users
				WHERE
					role='driver' AND
					from_city=%s AND
					to_city=%s
			""",
			(data["from_city"], data["to_city"])
		)
		drivers = cur.fetchall()

		# Send to all drivers + insert into ride_notifications
		for driver in drivers:
			try:
				cur.execute(
					"""
						INSERT INTO ride_notifications (ride_id, driver_id)
						VALUES (%s, %s)
						ON DUPLICATE KEY UPDATE notified_at=NOW()
					""",
					(request_id, driver["id"])
				)
				conn.commit()

				await message.bot.send_message(
					driver["telegram_id"],
					f"🚕 Yangi so'rov!\n"
					f"👤 Yo'lovchi: {message.from_user.full_name}\n"
					f"📍 Yo'nalish: {data["from_city"]} → {data["to_city"]}\n"
					f"💺 O'rindiqlar: {data["seats"]}\n"
					f"☎️ Telefon: {phone}\n",
					reply_markup=helper.driver_accept_kb(request_id)
				)
				print(f"✅ Sent to driver {driver['name']} ({driver['telegram_id']})")

			except Exception as e: print(f"⚠️ Could not notify {driver['name']}: {e}")

	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e}")
		await state.clear()
		return

	finally:
		cur.close()
		conn.close()

	# Notify passenger
	await message.answer(
		"✅ So'rovingiz qabul qilindi.\n"
		"☎️ Tez orada haydovchi siz bilan bog'lanadi.",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()
