from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import Any
from datetime import datetime, timedelta

def build_kb(
	options: list[Any],
	exclude: Any | None = None,
	per_row: int = 2
) -> ReplyKeyboardMarkup:
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

def get_date_options(days: int = 3) -> list[str]:
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


def yes_no_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo‘q")]
		],
		resize_keyboard=True
	)

