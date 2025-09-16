from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

import mysql.connector
from database.db import get_connection
from dictionary import NAVIGATE_BACK, NAVIGATE_HOME, RESTART, REQUEST_A_RIDE, REGISTER_AS_DRIVER, CANCEL_REQUEST

# -------------------- Menu acions
def main_menu_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[
				KeyboardButton(text=REQUEST_A_RIDE),
				KeyboardButton(text=REGISTER_AS_DRIVER)
			]
		],
		resize_keyboard=True
	)

async def set_bot_commands(bot):
	commands = [BotCommand(command="start", description=RESTART)]
	await bot.set_my_commands(commands)





# -------------------- Form acions
def build_kb(options, per_row) -> ReplyKeyboardMarkup:
	# group into rows
	rows, row = [], []
	for opt in options:
		row.append(KeyboardButton(text=str(opt)))
		if per_row and len(row) == per_row:
			rows.append(row)
			row = []
	if row: rows.append(row)

	# Always add navigation buttons
	rows.append([KeyboardButton(text=NAVIGATE_BACK), KeyboardButton(text=NAVIGATE_HOME)])

	return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def cancel_request_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text=CANCEL_REQUEST)]
		],
		resize_keyboard=True
	)

def driver_accept_kb(request_id: int):
	return InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(
				text="✅ So'rovni qabul qilish",
				callback_data=f"accept:{request_id}"
			)
		]
	])

def cancel_driver_kb(request_id):
	return InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(
				text="❌ Haydovchini bekor qilish",
				callback_data=f"cancel_driver:{request_id}"
			)
		]
	])





# -------------------- DB acions
def save_driver(telegram_id, name, phone, from_city, to_city):
	conn = get_connection()
	cur = conn.cursor()

	cur.execute(
		"""
			INSERT INTO users (telegram_id, role, name, phone, from_city, to_city)
			VALUES (%s, 'driver', %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				role='driver',
				name=VALUES(name),
				phone=VALUES(phone),
				from_city=VALUES(from_city),
				to_city=VALUES(to_city)
		""",
		(telegram_id, name, phone, from_city, to_city)
	)
	conn.commit()
	cur.close()
	conn.close()

def save_passenger(telegram_id, name, phone):
	conn = get_connection()
	cur = conn.cursor()
	try:
		cur.execute(
			"""
				INSERT INTO users (telegram_id, role, name, phone)
				VALUES (%s, 'passenger', %s, %s)
				ON DUPLICATE KEY UPDATE
					role = VALUES(role),
					name = VALUES(name),
					phone = VALUES(phone),
					id = LAST_INSERT_ID(id)
			""",
			(telegram_id, name, phone)
		)
		conn.commit()
		user_id = cur.lastrowid
	except mysql.connector.Error as e: print(f"❌ Database error: {e}")

	finally:
		cur.close()
		conn.close()

	return user_id

def save_passenger_ride(
	passenger_id,
	passenger_name,
	from_city,
	to_city,
	seats,
	passenger_phone
):
	conn = get_connection()
	cur = conn.cursor()

	try:
		cur.execute(
			"""
				INSERT INTO ride_requests
				(
					passenger_id,
					from_city,
					to_city,
					seats,
					passenger_name,
					passenger_phone,
					status
				)
				VALUES (%s, %s, %s, %s, %s, %s, 'pending')
			""",
			(
				passenger_id,
				from_city,
				to_city,
				seats,
				passenger_name,
				passenger_phone
			)
		)
		conn.commit()
		request_id = cur.lastrowid
	except mysql.connector.Error as e: print(f"❌ Database error: {e}")

	finally:
		cur.close()
		conn.close()

	return request_id
