from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand

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

async def set_bot_commands(bot):
	commands = [BotCommand(command="start", description="🔄 Qayta ishga tushirish")]
	await bot.set_my_commands(commands)
