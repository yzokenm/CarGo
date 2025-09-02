from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import mysql.connector
from database.config import DB_CONFIG, CITIES, SEAT_OPTIONS, TIME_OPTIONS
from database.db import get_connection
from handlers.matches import find_matching_trips

passenger_router = Router()

class PassengerForm(StatesGroup):
	from_city = State()
	to_city = State()
	date = State()
	time_pref = State()
	seats = State()

# --- Keyboards ---
def cities_kb(exclude: str | None = None) -> ReplyKeyboardMarkup:
	cities = [city for city in CITIES if city != exclude] if exclude else CITIES
	return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=city)] for city in cities], resize_keyboard=True)

def dates_kb(days: int = 3) -> ReplyKeyboardMarkup:
	today = datetime.now().date()
	return ReplyKeyboardMarkup(
		keyboard=[[KeyboardButton(text=(today + timedelta(days=i)).strftime("%Y-%m-%d"))] for i in range(days)],
		resize_keyboard=True
	)

def time_pref_kb() -> ReplyKeyboardMarkup:
	return ReplyKeyboardMarkup(
		keyboard=[[KeyboardButton(text=opt)] for opt in TIME_OPTIONS],
		resize_keyboard=True
	)

def seats_kb() -> ReplyKeyboardMarkup:
	return ReplyKeyboardMarkup(
		keyboard=[[KeyboardButton(text=str(n))] for n in SEAT_OPTIONS],
		resize_keyboard=True
	)

# --- DB Helpers ---
def ensure_user_and_get_id(telegram_id, name):
	conn = get_connection()
	cur = conn.cursor()
	cur.execute("""
		INSERT INTO users (telegram_id, role, name)
		VALUES (%s, 'passenger', %s)
		ON DUPLICATE KEY UPDATE role=VALUES(role), name=VALUES(name)
	""", (telegram_id, name))
	conn.commit()
	cur.execute("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
	user_id = cur.fetchone()[0]
	cur.close()
	conn.close()
	return user_id

def insert_request(passenger_id, from_city, to_city, date_iso, time_pref, seats):
	conn = get_connection()
	cur = conn.cursor()
	cur.execute("""
		INSERT INTO requests (passenger_id, from_city, to_city, date, time_pref, seats)
		VALUES (%s, %s, %s, %s, %s, %s)
	""", (passenger_id, from_city, to_city, date_iso, time_pref, seats))
	conn.commit()
	request_id = cur.lastrowid
	cur.close()
	conn.close()

	return request_id

# --- Flow ---
@passenger_router.message(F.text == "🧍 I’m a Passenger")
async def start_passenger_flow(message: Message, state: FSMContext):
	await state.set_state(PassengerForm.from_city)
	await message.answer("Select departure city:", reply_markup=cities_kb())

@passenger_router.message(PassengerForm.from_city)
async def handle_from_city(message: Message, state: FSMContext):
	city = message.text.strip()
	if city not in CITIES:
		await message.answer("Please choose a city from the menu:", reply_markup=cities_kb())
		return
	await state.update_data(from_city=city)
	await state.set_state(PassengerForm.to_city)
	await message.answer("Select destination city:", reply_markup=cities_kb(exclude=city))

@passenger_router.message(PassengerForm.to_city)
async def handle_to_city(message: Message, state: FSMContext):
	data = await state.get_data()
	from_city = data.get("from_city")
	dest = message.text.strip()
	if dest not in CITIES or dest == from_city:
		await message.answer("Please choose a *different* city:", reply_markup=cities_kb(exclude=from_city))
		return
	await state.update_data(to_city=dest)
	await state.set_state(PassengerForm.date)
	await message.answer("Pick your travel date:", reply_markup=dates_kb(days=3))

@passenger_router.message(PassengerForm.date)
async def handle_date(message: Message, state: FSMContext):
	raw = message.text.strip()
	try:
		dt = datetime.strptime(raw, "%Y-%m-%d").date()
	except ValueError:
		await message.answer("Please choose a valid date:", reply_markup=dates_kb(days=3))
		return
	today = datetime.now().date()
	if not (today <= dt <= today + timedelta(days=2)):
		await message.answer("Please choose one of the shown dates:", reply_markup=dates_kb(days=3))
		return
	await state.update_data(date=raw)
	await state.set_state(PassengerForm.time_pref)
	await message.answer("Preferred time of travel:", reply_markup=time_pref_kb())

@passenger_router.message(PassengerForm.time_pref)
async def handle_time_pref(message: Message, state: FSMContext):
	pref = message.text.strip()
	if pref not in TIME_OPTIONS:
		await message.answer("Please choose from the menu:", reply_markup=time_pref_kb())
		return
	await state.update_data(time_pref=pref)
	await state.set_state(PassengerForm.seats)
	await message.answer("Number of seats needed:", reply_markup=seats_kb())

@passenger_router.message(PassengerForm.seats)
async def handle_seats(message: Message, state: FSMContext):
	txt = message.text.strip()
	if not txt.isdigit() or int(txt) not in SEAT_OPTIONS:
		await message.answer("Please choose from the menu:", reply_markup=seats_kb())
		return
	await state.update_data(seats=int(txt))

	data = await state.get_data()
	from_city = data["from_city"]
	to_city = data["to_city"]
	date = data["date"]
	time_pref = data["time_pref"]
	seats = int(data["seats"])

	# Save passenger + request
	try:
		passenger_id = ensure_user_and_get_id(message.from_user.id, message.from_user.full_name)
		request_id = insert_request(passenger_id, from_city, to_city, date, time_pref, seats)

		# Get all registered drivers
		conn = get_connection()
		cur = conn.cursor(dictionary=True)
		cur.execute("SELECT telegram_id, name FROM users WHERE role='driver'")
		drivers = cur.fetchall()
		cur.close()
		conn.close()

	except mysql.connector.Error as e:
		await message.answer(f"❌ Database error: {e.msg}", reply_markup=ReplyKeyboardRemove())
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
				f"⏰ Vaqt: {time_pref}\n"
				f"💺 O'rindiqlar: {seats}\n\n"
				f"☎️ Passenger will wait for your call."
			)
		except Exception:
			# ignore errors if driver blocked the bot
			pass

	# Notify passenger
	await message.answer(
		"✅ Your ride request has been sent to nearby drivers.\n"
		"☎️ A driver will contact you soon.",
		reply_markup=ReplyKeyboardRemove()
	)

	await state.clear()

