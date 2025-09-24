from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

from database.Mysql import Mysql
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
	# 1. Ensure user exists
	Mysql.execute(
		sql="""
			INSERT INTO users (telegram_id, name, phone)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				name = VALUES(name),
				phone = VALUES(phone)
		""",
		params=[telegram_id, name, phone],
		commit=True
	)

	# 2. Get user_id
	user_row = Mysql.execute(
		sql="SELECT id FROM users WHERE telegram_id = %s",
		params=[telegram_id],
		fetchone=True
	)
	user_id = user_row["id"] if user_row else None

	if not user_id: return "error_user_not_found"

	# 3. Check if driver exists
	existing_driver = Mysql.execute(
		sql="SELECT id FROM drivers WHERE user_id = %s",
		params=[user_id],
		fetchone=True
	)

	if existing_driver: return "driver_exist"

	# 4. Insert new driver
	Mysql.execute(
		sql="""
			INSERT INTO drivers (user_id, from_city, to_city, car_status, is_contract_signed)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				from_city = VALUES(from_city),
				to_city   = VALUES(to_city),
				car_status = VALUES(car_status),
				is_contract_signed = VALUES(is_contract_signed)
		""",
		params=[user_id, from_city, to_city, car_status, is_contract_signed],
		commit=True
	)
