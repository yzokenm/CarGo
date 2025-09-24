from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

import mysql.connector
from database.db import get_connection
from dictionary import NAVIGATE_BACK, NAVIGATE_HOME, RESTART, REQUEST_A_RIDE, REGISTER_AS_DRIVER, CANCEL_REQUEST, CONTACT_US, HOW_IT_WORKS

# -------------------- Menu acions --------------------
def main_menu_kb():
	options = [REQUEST_A_RIDE, REGISTER_AS_DRIVER, CONTACT_US, HOW_IT_WORKS]
	return build_kb(options, per_row=2, include_navigation=False)

async def set_bot_commands(bot):
	commands = [BotCommand(command="start", description=RESTART)]
	await bot.set_my_commands(commands)





# -------------------- Form acions --------------------
def build_kb(options, per_row, include_navigation=True) -> ReplyKeyboardMarkup:
	# group into rows
	rows, row = [], []
	for opt in options:
		row.append(KeyboardButton(text=str(opt)))
		if per_row and len(row) == per_row:
			rows.append(row)
			row = []
	if row: rows.append(row)

	# Always add navigation buttons
	if include_navigation: rows.append([KeyboardButton(text=NAVIGATE_BACK), KeyboardButton(text=NAVIGATE_HOME)])

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
				text="❌ Bekor qilish",
				callback_data=f"cancel_driver:{request_id}"
			)
		]
	])





# -------------------- DB acions --------------------
def save_driver(
	telegram_id,
	name,
	phone,
	from_city,
	to_city,
	car_status="standard",
	is_contract_signed=False
):
	conn = get_connection()
	cur = conn.cursor()

	# 1. Save user to users table
	cur.execute(
		"""
		INSERT INTO users (telegram_id, name, phone)
		VALUES (%s, %s, %s)
		ON DUPLICATE KEY UPDATE
			name = VALUES(name),
			phone = VALUES(phone)
		""",
		(telegram_id, name, phone)
	)
	conn.commit()

	# Get user_id
	cur.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
	user_id = cur.fetchone()[0]

	# 2. Check if driver already exists
	cur.execute("SELECT id FROM drivers WHERE user_id = %s", (user_id,))
	existing_driver = cur.fetchone()

	if existing_driver:
		cur.close()
		conn.close()
		return "driver_exist"

	# 2. Insert driver
	cur.execute(
		"""
		INSERT INTO drivers (user_id, from_city, to_city, car_status, is_contract_signed)
		VALUES (%s, %s, %s, %s, %s)
		ON DUPLICATE KEY UPDATE
			from_city = VALUES(from_city),
			to_city   = VALUES(to_city),
			car_status = VALUES(car_status),
			is_contract_signed = VALUES(is_contract_signed)
		""",
		(user_id, from_city, to_city, car_status, is_contract_signed)
	)
	conn.commit()

	cur.close()
	conn.close()
