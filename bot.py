
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
rows = page.query_selector_all("table tbody tr")

numbers_list = []

for row in rows:
    cols = row.query_selector_all("td")

    if len(cols) < 3:
        continue

    # ✅ correct columns
    number = cols[1].inner_text().strip()
    range_name = cols[2].inner_text().strip()

    # ✅ clean number
    import re
    number = re.sub(r"\D", "", number)

    numbers_list.append({
        "country": range_name,
        "number": number
    })

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

    numbers = fetch_numbers(session)
    if not numbers:
        bot.send_message(msg.chat.id, "❌ No active numbers found")
        return

    user_sessions[msg.chat.id] = {"session": session}

    kb = InlineKeyboardMarkup()
    for n in numbers[:12]:
        kb.add(InlineKeyboardButton(n, callback_data=f"num|{n}"))

    bot.send_message(msg.chat.id, "📱 Select Number", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("num|"))
def select_number(call):
    number = call.data.split("|")[1]
    user_sessions.setdefault(call.message.chat.id, {})["number"] = number

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📩 GET OTP CODE", callback_data="getotp"))

    bot.edit_message_text(
        f"✅ Selected: <code>{number}</code>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "getotp")
def get_otp(call):
    data = user_sessions.get(call.message.chat.id)
    if not data:
        bot.answer_callback_query(call.id, "No session")
        return

    bot.answer_callback_query(call.id, "Checking OTP...")

    session = data.get("session")
    number = data.get("number")

    otp = fetch_otp(session, number)
    if otp:
        bot.send_message(call.message.chat.id, f"✅ OTP FOUND\n\n{otp}")
    else:
        bot.send_message(call.message.chat.id, "⏳ OTP not received yet")

# ================= START =================
print(">> IVAS HTTP BOT STARTED")
bot.infinity_polling(skip_pending=True)
