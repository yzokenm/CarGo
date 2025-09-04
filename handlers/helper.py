from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta

def build_kb(options, exclude=None, per_row=None) -> ReplyKeyboardMarkup:
	filtered = [opt for opt in options if opt != exclude]

	# group into rows
	rows = []
	row = []
	for opt in filtered:
		row.append(KeyboardButton(text=str(opt)))
		if len(row) == per_row:
			rows.append(row)
			row = []
	if row: rows.append(row)

	return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def phone_request_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text="📞 Share my phone number", request_contact=True)]
		],
		resize_keyboard=True,
		one_time_keyboard=True
	)

def get_date_options(days):
	today = datetime.now().date()
	options = []

	for i in range(days):
		date = today + timedelta(days=i)

		match i:
			case 0:
				label = "Bugun"
			case 1:
				label = "Ertaga"
			case 2:
				label = "Indinga"
			case _:
				label = date.strftime("%A")

		options.append(f"{label} ({date.strftime('%Y-%m-%d')})")

	return options
