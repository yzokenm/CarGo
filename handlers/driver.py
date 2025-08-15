from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import re
import mysql.connector
from database.config import DB_CONFIG, CITIES, SEAT_OPTIONS, PRICE_OPTIONS
from database.db import get_connection

driver_router = Router()

# ----- States -----
class DriverForm(StatesGroup):
	departure_city = State()
	destination_city = State()
	departure_date = State()
	seats_available = State()
	price = State()
	phone_number = State()

# ----- Keyboards -----
def cities_kb(exclude: str | None = None) -> ReplyKeyboardMarkup:
	cities = [city for city in CITIES if city != exclude] if exclude else CITIES
	rows = [[KeyboardButton(text=city)] for city in cities]
	return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def seats_kb() -> ReplyKeyboardMarkup:
	return ReplyKeyboardMarkup(
		keyboard=[[KeyboardButton(text=str(n)) for n in SEAT_OPTIONS]],
		resize_keyboard=True
	)

def price_kb() -> ReplyKeyboardMarkup:
	rows = [[KeyboardButton(text=f"{p:,} UZS".replace(",", " "))] for p in PRICE_OPTIONS]
	return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def phone_request_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text="📞 Share my phone number", request_contact=True)]
		],
		resize_keyboard=True,
		one_time_keyboard=True
	)

def dates_kb(days: int = 3) -> ReplyKeyboardMarkup:
	today = datetime.now().date()
	rows = [
		[KeyboardButton(text=(today + timedelta(days=i)).strftime("%Y-%m-%d"))]
		for i in range(days)
	]
	return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


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
					seats_available,
					price,
					phone_number
				)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
		""",
		(
			driver_id,
			dep_city,
			dest_city,
			dep_datetime,
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
	await message.answer("Select departure city:", reply_markup=cities_kb())

@driver_router.message(DriverForm.departure_city)
async def handle_departure_city(message: Message, state: FSMContext):
	city = message.text.strip()
	if city not in CITIES:
		await message.answer("Please choose a city from the menu:", reply_markup=cities_kb())
		return
	await state.update_data(departure_city=city)
	await state.set_state(DriverForm.destination_city)
	await message.answer("Select destination city:", reply_markup=cities_kb(exclude=city))

@driver_router.message(DriverForm.destination_city)
async def handle_destination_city(message: Message, state: FSMContext):
	data = await state.get_data()
	dep_city = data.get("departure_city")
	dest = message.text.strip()
	if dest not in CITIES or dest == dep_city:
		await message.answer("Please choose a *different* city from the menu:", reply_markup=cities_kb(exclude=dep_city))
		return
	await state.update_data(destination_city=dest)
	await state.set_state(DriverForm.departure_date)
	await message.answer("Pick your departure date:", reply_markup=dates_kb(days=3))

@driver_router.message(DriverForm.departure_date)
async def handle_departure_date(message: Message, state: FSMContext):
	raw = message.text.strip()
	# Expecting YYYY-MM-DD
	try:
		dt = datetime.strptime(raw, "%Y-%m-%d").date()
	except ValueError:
		await message.answer("Please pick a date from the menu (format YYYY-MM-DD):", reply_markup=dates_kb(days=3))
		return
	# Optional: only allow today..today+2
	today = datetime.now().date()
	if not (today <= dt <= today + timedelta(days=2)):
		await message.answer("Please select one of the shown dates:", reply_markup=dates_kb(days=3))
		return
	await state.update_data(departure_date=raw)
	await state.set_state(DriverForm.seats_available)
	await message.answer("Select number of available seats:", reply_markup=seats_kb())

@driver_router.message(DriverForm.seats_available)
async def handle_seats(message: Message, state: FSMContext):
	txt = message.text.strip()
	if not txt.isdigit() or int(txt) not in SEAT_OPTIONS:
		await message.answer("Please choose seats from the menu:", reply_markup=seats_kb())
		return
	await state.update_data(seats_available=int(txt))
	await state.set_state(DriverForm.price)
	await message.answer("Select price per seat:", reply_markup=price_kb())

@driver_router.message(DriverForm.price)
async def handle_price(message: Message, state: FSMContext):
	# Accept "100 000 UZS" or "100000"
	cleaned = re.sub(r"[^\d.]", "", message.text)
	if not cleaned or not cleaned.isdigit():
		# Restrict to menu for now
		await message.answer("Please choose a price from the menu:", reply_markup=price_kb())
		return
	price = float(cleaned)
	await state.update_data(price=price)
	await state.set_state(DriverForm.phone_number)
	await message.answer("📱 Please share your phone number:", reply_markup=phone_request_kb())

@driver_router.message(DriverForm.phone_number, F.content_type == "contact")
async def save_phone(message: Message, state: FSMContext):
	if message.contact: phone_number = message.contact.phone_number
	else: phone_number = message.text

	await state.update_data(phone_number=phone_number)

	data = await state.get_data()

	departure_city = data["departure_city"]
	destination_city = data["destination_city"]
	departure_date = data["departure_date"]
	seats = int(data["seats_available"])
	price = float(data["price"])
	phone_number = data["phone_number"]

	try:
		driver_id = ensure_user_and_get_id(message.from_user.id, message.from_user.full_name)
		insert_trip(driver_id, departure_city, destination_city, departure_date, seats, price, phone_number)
	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())
		await state.clear()
		return

	price_label = f"{int(price):,} UZS".replace(",", " ")
	await message.answer(
		"✅ Trip posted successfully!\n"
		f"From: {departure_city}\n"
		f"To: {destination_city}\n"
		f"Date: {departure_date}\n"
		f"Seats: {seats}\n"
		f"Price: {price_label}\n"
		f"Phone: {phone_number}",
		reply_markup=ReplyKeyboardRemove()
	)
	await state.clear()
