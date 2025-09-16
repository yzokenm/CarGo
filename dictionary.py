# Route directions
DIRECTIONS = ["🚖 Viloyatdan → Toshkentga", "🚖 Toshkentdan → Viloyatga"]
CITIES_TO_TASHKENT = ["Andijan → Toshkent", "Farg'ona → Toshkent", "Shaxrixon → Toshkent", "Qo'qon → Toshkent", "Namangan → Toshkent"]
CITIES_FROM_TASHKENT = ["Toshkent → Andijan", "Toshkent → Shaxrixon", "Toshkent → Namangan", "Toshkent → Qo'qon", "Toshkent → Namangan"]

# Available seats
SEAT_OPTIONS = [1, 2, 3, 4, 5]

# User role selecton routes
REQUEST_A_RIDE = "🚖 Taksi buyurtma berish"
REGISTER_AS_DRIVER = "🧑‍✈️ Taksida ishlash"

# Navigation routes
RESTART = "🔄 Qayta ishga tushirish"
NAVIGATE_BACK = "⬅️ Orqaga"
NAVIGATE_HOME = "🏠 Asosiy menyu"
CANCEL_REQUEST = "🚫 Bekor qilish"

# Contact us and About Us routes
CONTACT_US = "☎️ Biz bilan bog'lanish"
ABOUT_US = "ℹ️ Biz haqimizda"

# /start route intro
MAIN_INTRO = "🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatga safar qilmoqchimisiz? \n\n 📲 CarGo botida buyurtma bering!"

# Contact us route message
ABOUT_US_MSG = """
	CarGoBot - Viloyatlararo taxi xizmati 🚖\n
	CarGoBot sizning qulay va xavfsiz sayohatingiz uchun yaratilgan zamonaviy Telegram botidir.\n
	Afzalliklarimiz:
	🔰Tez va oson buyurtma – Faqat bir necha tugmani bosib, yo‘nalishingiz va manzilingizni kiriting, kerakli taksini darhol topasiz.\n
	⚠️Xavfsizlik va Ishonchlilik: Botda taksi haydovchilari malakali va tajribali bo'lib, har bir yo'lovchi uchun qulay va xavfsiz sayohatni ta'minlaydi.\n
	❓Qanday ishlaydi?\n
	1️⃣ Telegramda <a href="https://t.me/cargofastbot"><b><i>CarGoFastBot</i></b></a> ni oching.\n
	2️⃣ “Start” tugmasini bosing.\n
	3️⃣ Manzilingiz va borish joyingizni kiriting.\n
	4️⃣ Haydovchilarimiz qisqa vaqt ichida siz bilan bog‘lanishadi.\n
	🚀CarGoBot - bu zamonaviy va foydalanuvchilarga qulaylik yaratish uchun yaratilgan xizmat bo'lib, viloyatlar aro sayohatlarni oson va tez amalga oshirish imkoniyatini beradi. Endi sayohat qilishning yangi usulidan bahramand bo'ling!
"""

CONTACT_US_MSG = """
	🚖 CarGo – Viloyatlararo taksi xizmati!\n
	☎️ Call Center: +99895 036 10 99
	💬 Telegram yordam: @yzoken\n
	🚗 Tez va aniq manzilga yetkazamiz
	🛡 Har safarda xavfsizlik kafolatlangan
	🛋 Siz uchun qulay sharoitda yo‘l\n
	💛 CarGo bilan – yo‘lingiz doim ishonchli!
"""

# Phone number regex (+9989901234567)
phone_number_regEx = r"^\+?998\d{9}$"

# DISCLAIMERS
# Invalid input value
INVALID_COMMAND = """
	❌ Noma'lum buyruq!\n
	<i>Siz bot chatiga bevosita xabar yubordingiz yoki
	bot sozlamalari o‘zgartirilgan bo‘lishi mumkin.</i>

	ℹ️ Iltimos, botga to'g'ridan-to'g'ri yozmang.
	Botdan foydalanish uchun <a href="https://t.me/cargofastbot?start=1">/start</a> tugmasini bosib menyuni yangilang.
"""
