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




# /start route intro
MAIN_INTRO = "🚖 Viloyatdan Toshkentga yoki Toshkentdan viloyatga safar qilmoqchimisiz? \n\n 📲 CarGo botida buyurtma bering!"

# How It Works route message
HOW_IT_WORKS = "📑 Bot qanday ishlaydi?"
HOW_IT_WORKS_MSG = """
	🚀 CarGo - Viloyatlararo taksi xizmati 🚖\n
	<a href="https://t.me/cargofastbot"><b><i>CarGoFastBot</i></b></a> sizning qulay va xavfsiz sayohatingiz uchun yaratilgan zamonaviy Telegram botidir.\n
	Afzalliklarimiz:
	🔰Tez va oson buyurtma - Faqat bir necha tugmani bosib, yo'nalishingiz va manzilingizni kiriting, kerakli taksini darhol topasiz.\n
	⚠️Xavfsizlik va Ishonchlilik: Botda taksi haydovchilari malakali va tajribali bo'lib, har bir yo'lovchi uchun qulay va xavfsiz sayohatni ta'minlaydi.\n
	❓Qanday ishlaydi?\n
	1️⃣ Telegramda <a href="https://t.me/cargofastbot"><b><i>CarGoFastBot</i></b></a> ni oching.\n
	2️⃣ “Start” tugmasini bosing.\n
	3️⃣ Manzilingiz va borish joyingizni kiriting.\n
	4️⃣ Haydovchilarimiz qisqa vaqt ichida siz bilan bog'lanishadi.\n
	🚀 CarGo - bu zamonaviy va foydalanuvchilarga qulaylik yaratish uchun yaratilgan xizmat bo'lib, viloyatlar aro sayohatlarni oson va tez amalga oshirish imkoniyatini beradi. Endi sayohat qilishning yangi usulidan bahramand bo'ling!
"""

# Contact us route message
CONTACT_US = "☎️ Biz bilan bog'lanish"
CONTACT_US_MSG = """
	🚖 CarGo - Viloyatlararo taksi xizmati!\n
	☎️ Call Center: +99895 036 10 99
	💬 Telegram yordam: @yzoken\n
	🚗 Tez va aniq manzilga yetkazamiz
	🛡 Har safarda xavfsizlik kafolatlangan
	🛋 Siz uchun qulay sharoitda yo'l\n
	💛 CarGo bilan - yo'lingiz doim ishonchli!
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


# Terms And Conditions
TERMS_AND_CONDITIONS_TEXT = "✅ Roziman"
TERMS_AND_CONDITIONS_MSG = """
	■ HAYDOVCHI BILAN SHARTNOMA\n
	Ushbu shartnoma <i>“CarGo”</i> platformasi (keyingi o'rinlarda “Platforma”) va haydovchi (keyingi
	o'rinlarda “Haydovchi”) o'rtasida tuziladi.
	Shartnomaning asosiy maqsadi - yo'lovchilarga xavfsiz, qulay va sifatli transport xizmatini
	ta'minlashdir.\n
	1. UMUMIY QOIDALAR
	1.1. Platforma - yo'lovchi va haydovchi o'rtasida vositachi bo'lib xizmat qiladi.
	1.2. Haydovchi o'z faoliyati uchun to'liq javobgar bo'ladi.
	1.3. Yo'lovchi doim haqli - haydovchi esa mijozga hurmat bilan xizmat ko'rsatishi shart.
	2. TO'LOVLAR VA QOIDALAR
	2.1. Platforma xozircha haydovchidan hech qanday mablag' talab qilmaydi va mutlaq bepul.
	2.3. Haydovchi faqat o'z hisobidan xizmat qiladi va olingan buyurtmalar uchun mustaqil javobgar
	bo'ladi.
	3. HAYDOVCHI MAJBURIYATLARI
	3.1. Yo'lovchi bilan doimo xushmuomala bo'lish.
	3.2. Transport vositasi toza, ozoda va texnik jihatdan soz bo'lishi.
	3.3. Xizmat jarayonida barcha yo'l harakati qoidalariga rioya qilish.
	3.4. Yo'lovchini xavfsiz va belgilangan manzilga yetkazib qo'yish.
	3.5. Platforma tomonidan belgilangan barcha qoidalarga rioya qilish.
	4. PLATFORMANING HUQUQLARI
	4.1. Haydovchi qoidabuzarlik qilgan taqdirda, uni platformadan chetlatish huquqiga ega.
	4.2. Yo'lovchilardan tushgan shikoyatlar tekshiriladi va zarur chora ko'riladi.
	4.3. Platforma haydovchining shaxsiy xatti-harakatlari uchun javobgar emas.
	5. YAKUNIY QOIDALAR
	5.1. Ushbu shartnoma muddatsiz tuzilgan bo'lib, tomonlardan biri uni bekor qilishni xohlasa,
	oldindan ogohlantirishi shart.
	5.2. Har qanday nizolar O'zbekiston Respublikasining amaldagi qonunlariga muvofiq hal etiladi.
"""
