from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from typing import Any

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
