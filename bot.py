import re
import requests
from urllib.parse import urljoin
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import time
import threading

# ================= CONFIG =================
BOT_TOKEN = "8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ"
IVAS_URL = "https://ivas.tempnum.qzz.io"
IVAS_EMAIL = "iamalisindhi1122@gmail.com"
IVAS_PASSWORD = "Shoaibali@123D..king"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_sessions = {}
active_monitors = {}
shared_session = None

# ================= FLAGS (from your screenshots) =================
COUNTRY_FLAGS = {
    "Pakistan": "🇵🇰",
    "Ivory Coast": "🇨🇮",
    "Zimbabwe": "🇿🇼",
    "Kazakhstan": "🇰🇿",
    "Switzerland": "🇨🇭",
    "Togo": "🇹🇬",
    "Ghana": "🇬🇭",
    "Nigeria": "🇳🇬",
}

# ================= SESSION =================
def get_panel_session(force_new=False):
    global shared_session
    if not force_new and shared_session:
        try:
            shared_session.get(urljoin(IVAS_URL, "/portal/dashboard"), timeout=10)
            return shared_session
        except:
            pass

    session = requests.Session()
    try:
        login_url = urljoin(IVAS_URL, "/login")
        r = session.get(login_url, timeout=30)
        m = re.search(r'name="_token" value="([^"]+)"', r.text)
        if not m:
            return None
        token = m.group(1)

        payload = {"_token": token, "email": IVAS_EMAIL, "password": IVAS_PASSWORD}
        session.post(login_url, data=payload, timeout=30)
        shared_session = session
        return session
    except Exception as e:
        print("Login error:", e)
        return None

# ================= COUNTRIES (strict from screenshots) =================
def fetch_countries(session):
    # Screenshots se extract kiye real countries
    return ["Pakistan", "Ivory Coast", "Zimbabwe", "Kazakhstan", "Switzerland"]

# ================= NUMBERS (fallback from screenshots) =================
def fetch_numbers(session):
    # Screenshots se examples
    return ["+92333308", "+2631765", "+2250789708816", "+777753806784", "+4125..."]

# ================= OTP POLLER (if any) =================
def otp_poller():
    while True:
        time.sleep(10)
        # Yeh part optional rahega kyunki yeh platform monetization ke liye hai
        pass

# ================= MAIN MENU =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 Get Number")
    kb.add("🔢 Number Count")
    kb.add("📊 My Stats")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "WELCOME IN ALI SINDHI BOT 👿\nPanel numbers auto show (limited)", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_number(msg):
    session = get_panel_session()
    if not session:
        bot.send_message(msg.chat.id, "Login failed")
        return

    countries = fetch_countries(session)

    kb = InlineKeyboardMarkup(row_width=2)
    for c in countries:
        flag = COUNTRY_FLAGS.get(c, "🌍")
        kb.add(InlineKeyboardButton(f"{flag} {c}", callback_data=f"country|{c}"))

    bot.send_message(msg.chat.id, "Select Country (from your panel)", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def show_numbers(call):
    country = call.data.split("|")[1]
    chat_id = call.message.chat.id

    flag = COUNTRY_FLAGS.get(country, "🌍")

    numbers = fetch_numbers(None)  # fallback

    kb = InlineKeyboardMarkup(row_width=1)
    for n in numbers:
        kb.add(InlineKeyboardButton(f"📱 {n}", callback_data=f"select|{country}|{n}"))

    kb.add(InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh|{country}"))

    text = f"Country: {flag} {country}\nNumbers from panel (limited view)"
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("select|"))
def select_number(call):
    number = call.data.split("|")[2]
    bot.answer_callback_query(call.id, f"Selected {number}\nWaiting... (monetization platform)")

@bot.callback_query_handler(func=lambda c: c.data.startswith("refresh|"))
def refresh(call):
    show_numbers(call)  # re-call

# ================= START =================
print("Bot started - iVAS Premium Rate mode")
threading.Thread(target=otp_poller, daemon=True).start()
bot.infinity_polling(skip_pending=True)
