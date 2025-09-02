from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def role_selection_kb():
	return ReplyKeyboardMarkup(
		keyboard=[
			[
				KeyboardButton(text="🚖 Order a Ride"),
				KeyboardButton(text="🧑‍✈️ Register as Driver")
			]
		],
		resize_keyboard=True
	)
