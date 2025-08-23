from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import re
from datetime import datetime, timedelta

import mysql.connector
from database.config import DB_CONFIG, CITIES, SEAT_OPTIONS, PRICE_OPTIONS
from database.db import get_connection
from handlers import helper

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	departure_city = State()
	destination_city = State()
	departure_date = State()
	seats_available = State()
	has_post = State()
	price = State()
	phone_number = State()

def ensure_user_and_get_id(telegram_id: int, name: str) -> int:
	connection = get_connection()
	cursor = connection.cursor()
	cursor.execute(
		"""
			INSERT INTO users
				(
					telegram_id,
					role,
					name
				)
			VALUES (%s, 'driver', %s)
			ON DUPLICATE KEY UPDATE role=VALUES(role), name=VALUES(name)
		""",
		(telegram_id, name)
	)
	connection.commit()
	cursor.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
	user_id = cursor.fetchone()[0]
	cursor.close()
	connection.close()

	return user_id

def insert_trip(
		driver_id: int,
		dep_city: str,
		dest_city: str,
		dep_date_iso: str,
		has_post: str,
		seats: int,
		price: float,
		phone_number: int
	):

	# Store as DATETIME; we’re using midnight since only a date is chosen.
	dep_datetime = f"{dep_date_iso} 00:00:00"
	connection = get_connection()
	cursor = connection.cursor()
	cursor.execute(
		"""
			INSERT INTO trips
				(
					driver_id,
					departure_city,
					destination_city,
					departure_time,
					has_post,
					seats_available,
					price,
					phone_number
				)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
		""",
		(
			driver_id,
			dep_city,
			dest_city,
			dep_datetime,
			has_post,
			seats,
			price,
			phone_number
		)
	)
	connection.commit()
	cursor.close()
	connection.close()

# --- Route Start ---
@driver_router.message(F.text == "🚖 I’m a Driver")
async def start_driver_flow(message: Message, state: FSMContext):
	await state.set_state(DriverForm.departure_city)
	kb = helper.build_kb(CITIES, exclude="Shaxrixon", per_row=2)
	await message.answer("Jo'nab ketish manzilini tanlang:", reply_markup=kb)


@driver_router.message(DriverForm.departure_city)
async def handle_departure_city(message: Message, state: FSMContext):
	city = message.text.strip()
	if city not in CITIES:
		kb = helper.build_kb(CITIES, per_row=2)
		await message.answer("Iltimos, menyudagi shaharni tanlang:", reply_markup=kb)
		return

	await state.update_data(departure_city=city)
	await state.set_state(DriverForm.destination_city)
	kb = helper.build_kb(CITIES, exclude=city, per_row=2)
	await message.answer("Yetib borish manzilini tanlang:", reply_markup=kb)


@driver_router.message(DriverForm.destination_city)
async def handle_destination_city(message: Message, state: FSMContext):
	data = await state.get_data()
	dep_city = data.get("departure_city")
	dest = message.text.strip()

	if dest not in CITIES or dest == dep_city:
		kb = helper.build_kb(CITIES, exclude=dep_city, per_row=2)
		await message.answer("Menyudan *boshqa* shaharni tanlang:", reply_markup=kb)
		return

	await state.update_data(destination_city=dest)
	await state.set_state(DriverForm.departure_date)
	DATE_OPTIONS = helper.get_date_options(days=3)
	kb = helper.build_kb(DATE_OPTIONS, per_row=2)
	await message.answer("Ketish sanasini tanlang:", reply_markup=kb)


@driver_router.message(DriverForm.departure_date)
async def handle_departure_date(message: Message, state: FSMContext):
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

	await state.update_data(departure_date=dt.strftime("%Y-%m-%d"))
	# 👇 instead of seats → ask about post
	await state.set_state(DriverForm.has_post)
	await message.answer("Post qabul qilasizmi?", reply_markup=helper.yes_no_kb())


@driver_router.message(DriverForm.has_post)
async def handle_has_post(message: Message, state: FSMContext):
	raw = message.text.strip()

	if raw not in ["✅ Ha", "❌ Yo‘q"]:
		await message.answer("Iltimos, Ha yoki Yo‘qni tanlang:", reply_markup=helper.yes_no_kb())
		return

	has_post = 1 if raw == "✅ Ha" else 0
	await state.update_data(has_post=has_post)

	# 👇 continue flow → ask about seats
	await state.set_state(DriverForm.seats_available)
	kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
	await message.answer("Mavjud o'rindiqlar sonini tanlang:", reply_markup=kb)


@driver_router.message(DriverForm.seats_available)
async def handle_seats(message: Message, state: FSMContext):
	txt = message.text.strip()
	if not txt.isdigit() or int(txt) not in SEAT_OPTIONS:
		kb = helper.build_kb(SEAT_OPTIONS, per_row=2)
		await message.answer("Iltimos, menyudagi o'rindiqlarni tanlang:", reply_markup=kb)
		return

	await state.update_data(seats_available=int(txt))
	await state.set_state(DriverForm.price)
	kb = helper.build_kb(PRICE_OPTIONS, per_row=2)
	await message.answer("Bir o'rindiq uchun narxni tanlang:", reply_markup=kb)


@driver_router.message(DriverForm.price)
async def handle_price(message: Message, state: FSMContext):
	cleaned = re.sub(r"[^\d.]", "", message.text)
	if not cleaned or not cleaned.isdigit():
		kb = helper.build_kb(PRICE_OPTIONS, per_row=2)
		await message.answer("Iltimos, menyudagi narxni tanlang:", reply_markup=kb)
		return

	price = float(cleaned)
	await state.update_data(price=price)
	await state.set_state(DriverForm.phone_number)
	await message.answer("📱 Iltimos, telefon raqamingizni ulashing:", reply_markup=helper.phone_request_kb())


@driver_router.message(DriverForm.phone_number, F.content_type == "contact")
async def save_phone(message: Message, state: FSMContext):
	if message.contact: phone_number = message.contact.phone_number
	else: phone_number = message.text

	await state.update_data(phone_number=phone_number)

	data = await state.get_data()

	departure_city = data["departure_city"]
	destination_city = data["destination_city"]
	departure_date = data["departure_date"]
	has_post = data["has_post"]
	seats = int(data["seats_available"])
	price = float(data["price"])
	phone_number = data["phone_number"]

	try:
		driver_id = ensure_user_and_get_id(message.from_user.id, message.from_user.full_name)
		insert_trip(driver_id, departure_city, destination_city, departure_date, has_post, seats, price, phone_number)
	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())
		await state.clear()
		return

	price_label = f"{int(price):,} UZS".replace(",", " ")
	has_post_label = "❌ Yo‘q" if has_post == 0 else "✅ Ha"
	await message.answer(
		"✅ Safaringiz muvaffaqiyatli chop etildi!\n"
		f"Dan: {departure_city}\n"
		f"Ga: {destination_city}\n"
		f"Sana: {departure_date}\n"
		f"Pochta olasizmi?: {has_post_label}\n"
		f"O'rindiqlar: {seats}\n"
		f"Narx: {price_label}\n"
		f"Telefon: {phone_number}",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()
