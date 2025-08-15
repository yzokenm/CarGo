from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def role_selection_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[KeyboardButton(text="🚖 I’m a Driver")],
			[KeyboardButton(text="🧍 I’m a Passenger")]
		],
		resize_keyboard=True
	)
