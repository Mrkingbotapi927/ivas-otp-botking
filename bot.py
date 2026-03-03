
import re
import requests
from urllib.parse import urljoin
import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ"
IVAS_URL = "https://ivas.tempnum.qzz.io"
IVAS_EMAIL = "iamalisindhi1122@gmail.com"
IVAS_PASSWORD = "Shoaibali@123D..king"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_sessions = {}

# ================= LOGIN SESSION =================
def get_panel_session():
    session = requests.Session()
    try:
        login_url = urljoin(IVAS_URL, "/login")
        r = session.get(login_url, timeout=30)

        m = re.search(r'name="_token" value="([^"]+)"', r.text)
        if not m:
            print("CSRF not found")
            return None
        token = m.group(1)

        payload = {
            "_token": token,
            "email": IVAS_EMAIL,
            "password": IVAS_PASSWORD
        }

        session.post(login_url, data=payload, timeout=30)
        return session
    except Exception as e:
        print("Login error:", e)
        return None

# ================= FETCH NUMBERS =================
def fetch_numbers(session):
    try:
        url = urljoin(IVAS_URL, "/portal/numbers")
        r = session.get(url, timeout=30)

        # only proper long numbers (10–15 digits)
        nums = re.findall(r"\b\d{10,15}\b", r.text)

        # remove duplicates
        nums = list(dict.fromkeys(nums))

        # ✅ LIMIT 200
        return nums[:200]

    except Exception as e:
        print("Fetch numbers error:", e)
        return []

# ================= FETCH OTP =================
def fetch_otp(session, number):
    try:
        url = urljoin(IVAS_URL, "/portal/sms/received")
        r = session.get(url, timeout=30)
        if number in r.text:
            return r.text[:1000]
    except Exception as e:
        print("OTP fetch error:", e)
    return None

# ================= UI =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 Get Number")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "✨ OTP Dashboard Ready", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_number(msg):
    bot.send_message(msg.chat.id, "🔄 Fetching numbers...")

    session = get_panel_session()
    if not session:
        bot.send_message(msg.chat.id, "❌ Login failed")
        return

    numbers = fetch_numbers(session)  # ✅ yahan define hota hai

    if not numbers:
        bot.send_message(msg.chat.id, "❌ No active numbers found")
        return

    user_sessions[msg.chat.id] = {"session": session}

    # ✅ keyboard yahin banana hai (andar hi)
    kb = InlineKeyboardMarkup(row_width=2)

    buttons = []
    for n in numbers:
        buttons.append(
            InlineKeyboardButton(
                f"📋 {n}",
                callback_data=f"copy|{n}"
            )
        )

    kb.add(*buttons)

    kb.add(
        InlineKeyboardButton("📩 GET OTP", callback_data="getotp_menu")
    )

    kb.add(
        InlineKeyboardButton("🔄 Refresh Numbers", callback_data="refresh_nums")
    )

    bot.send_message(
        msg.chat.id,
        "📱 Select Number",
        reply_markup=kb
    )
  )

# add number buttons
kb.add(*buttons)

# bottom controls
kb.add(
    InlineKeyboardButton("📩 GET OTP", callback_data="getotp_menu")
)

kb.add(
    InlineKeyboardButton("🔄 Refresh Numbers", callback_data="refresh_nums")
)

@bot.callback_query_handler(func=lambda c: c.data == "refresh_nums")
def refresh_numbers_cb(call):
    bot.answer_callback_query(call.id, "Refreshing...")

    msg = call.message

    session = get_panel_session()
    if not session:
        bot.send_message(msg.chat.id, "❌ Login failed")
        return

    numbers = fetch_numbers(session)
    if not numbers:
        bot.send_message(msg.chat.id, "❌ No AVAILABLE RANGE")
        return

    user_sessions[msg.chat.id] = {"session": session}

    kb = InlineKeyboardMarkup(row_width=2)

    buttons = []
    for n in numbers:
        buttons.append(
            InlineKeyboardButton(f"📋 {n}", callback_data=f"copy|{n}")
        )

    kb.add(*buttons)
    kb.add(InlineKeyboardButton("📩 GET OTP", callback_data="getotp_menu"))
    kb.add(InlineKeyboardButton("🔄 Refresh Numbers", callback_data="refresh_nums"))

    bot.edit_message_text(
        "📱 Select Number",
        msg.chat.id,
        msg.message_id,
        reply_markup=kb
    )

# ================= START =================
print(">> IVAS HTTP BOT STARTED")
bot.infinity_polling(skip_pending=True)
