import re
import requests
from urllib.parse import urljoin
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import time
import threading
import hashlib

# ================= CONFIG =================
BOT_TOKEN = "8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ"
IVAS_URL = "https://ivas.tempnum.qzz.io"
IVAS_EMAIL = "iamalisindhi1122@gmail.com"
IVAS_PASSWORD = "Shoaibali@123D..king"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_sessions = {}
active_monitors = {}
target_group_id = None
last_seen = set()
shared_session = None

# ================= FLAGS =================
COUNTRY_FLAGS = {
    "Pakistan": "🇵🇰", "Ivory Coast": "🇨🇮", "Zimbabwe": "🇿🇼", "Kazakhstan": "🇰🇿",
    "Switzerland": "🇨🇭", "Togo": "🇹🇬", "Ghana": "🇬🇭", "Nigeria": "🇳🇬",
    "India": "🇮🇳", "Bangladesh": "🇧🇩"
}

OWNER_CHAT_ID = None

# ================= SESSION =================
def get_panel_session(force_new=False):
    global shared_session
    if not force_new and shared_session:
        try:
            shared_session.get(urljoin(IVAS_URL, "/my-numbers"), timeout=10)
            return shared_session
        except:
            pass

    session = requests.Session()
    try:
        r = session.get(urljoin(IVAS_URL, "/login"), timeout=30)
        token = re.search(r'name="_token" value="([^"]+)"', r.text).group(1)
        payload = {"_token": token, "email": IVAS_EMAIL, "password": IVAS_PASSWORD}
        session.post(urljoin(IVAS_URL, "/login"), data=payload, timeout=30)
        shared_session = session
        return session
    except:
        return None

# ================= FETCH RANGES FROM PANEL (My Numbers) =================
def fetch_ranges(session):
    try:
        urls = ["/my-numbers", "/client/my-numbers", "/test-system/test-numbers", "/portal/my-numbers"]
        for path in urls:
            r = session.get(urljoin(IVAS_URL, path), timeout=20)
            if r.status_code != 200:
                continue
            text = r.text.upper()
            ranges = re.findall(r'(PAKISTAN|IVORY COAST|ZIMBABWE|KAZAKHSTAN|SWITZERLAND|TOGO|GHANA|NIGERIA|INDIA|BANGLADESH)\s*\d{3,8}', text)
            if ranges:
                return list(dict.fromkeys(ranges))
        return ["PAKISTAN 333308", "IVORY COAST 4040", "ZIMBABWE 1765", "KAZAKHSTAN 10777"]
    except:
        return ["PAKISTAN 333308", "IVORY COAST 4040"]

# ================= GET COUNTRIES =================
def get_countries(ranges):
    countries = set()
    for r in ranges:
        match = re.match(r'([A-Z ]+)', r)
        if match:
            countries.add(match.group(1).strip().title())
    return sorted(list(countries)) or ["Pakistan", "Ivory Coast"]

# ================= MAIN MENU =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("🚀 Get Number"))
    kb.add(KeyboardButton("🔄 Refresh Panel"))
    kb.add(KeyboardButton("📍 Set OTP Group"))
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    global OWNER_CHAT_ID
    OWNER_CHAT_ID = msg.chat.id
    bot.send_message(msg.chat.id, "👿 ALI SINDHI iVAS BOT READY\n\nPanel numbers auto sync + Group OTP", reply_markup=main_menu())

# ================= GET NUMBER → COUNTRIES WITH FLAGS =================
@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_countries_handler(msg):
    session = get_panel_session()
    ranges = fetch_ranges(session)
    countries = get_countries(ranges)

    kb = InlineKeyboardMarkup(row_width=2)
    for c in countries:
        flag = COUNTRY_FLAGS.get(c, "🌍")
        kb.add(InlineKeyboardButton(f"{flag} {c}", callback_data=f"country|{c}"))

    bot.send_message(msg.chat.id, "🌍 Select Country (Panel se auto loaded)", reply_markup=kb)

# ================= COUNTRY → 2 NUMBERS + COPY + NEXT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def show_numbers(call):
    country = call.data.split("|")[1]
    chat_id = call.message.chat.id
    session = get_panel_session(force_new=True)
    all_ranges = fetch_ranges(session)

    # Filter this country
    numbers = [r for r in all_ranges if country.upper() in r.upper()][:2]

    flag = COUNTRY_FLAGS.get(country, "🌍")

    kb = InlineKeyboardMarkup(row_width=1)
    for num in numbers:
        kb.add(InlineKeyboardButton(f"📱 {num}", callback_data=f"copy|{num}"))

    kb.add(InlineKeyboardButton("🔄 Next Number", callback_data=f"next|{country}"))
    kb.add(InlineKeyboardButton("← Back", callback_data="back"))

    text = f"Country: {flag} {country}\n\n📱 Available Numbers (2)\nSelect aur Copy karo"
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

# ================= COPY BUTTON =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("copy|"))
def copy_number(call):
    number = call.data.split("|")[1]
    bot.answer_callback_query(call.id, "✅ Copied!", show_alert=True)
    bot.send_message(call.message.chat.id, f"<code>{number}</code>\n\nCopy ho gaya 🔥", parse_mode="HTML")

# ================= NEXT NUMBER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("next|"))
def next_number(call):
    country = call.data.split("|")[1]
    bot.answer_callback_query(call.id, "🔄 Fresh numbers loading...")
    show_numbers(call)  # re-fetch

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(call):
    bot.answer_callback_query(call.id, "Back...")
    bot.send_message(call.message.chat.id, "Main menu", reply_markup=main_menu())

# ================= SET GROUP =================
@bot.message_handler(func=lambda m: m.text == "📍 Set OTP Group")
def set_group(msg):
    global target_group_id
    target_group_id = msg.chat.id
    bot.send_message(msg.chat.id, f"✅ OTP Group Set!\nGroup ID: {target_group_id}\nAb OTP yahan aayega")

# ================= REFRESH =================
@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Panel")
def refresh_panel(msg):
    bot.send_message(msg.chat.id, "🔄 Panel se fresh data liya ja raha hai...")
    get_countries_handler(msg)

# ================= OTP POLLER (Group + Notification) =================
def otp_poller():
    global target_group_id
    while True:
        time.sleep(7)
        if not target_group_id:
            continue
        session = get_panel_session()
        if not session:
            continue
        try:
            r = session.get(urljoin(IVAS_URL, "/sms-test-history"), timeout=15)
            text = r.text
            otps = re.findall(r'(PAKISTAN|IVORY COAST|ZIMBABWE|KAZAKHSTAN).*?(\d{4,8})', text, re.IGNORECASE)
            for country, otp in otps:
                key = hashlib.md5((country + otp).encode()).hexdigest()
                if key in last_seen:
                    continue
                last_seen.add(key)
                bot.send_message(target_group_id, f"📩 New OTP\nRange: {country}\nOTP: <code>{otp}</code>", parse_mode="HTML")
                if OWNER_CHAT_ID:
                    bot.send_message(OWNER_CHAT_ID, "✅ Aapki OTP chat group mein receive ho gai hai 🔥")
        except:
            pass

# ================= START =================
if __name__ == "__main__":
    print(">> ALI SINDHI iVAS FULL AUTO BOT STARTED ✅")
    print(">> Panel sync + Flags + Copy + Next Number + Group OTP")

    threading.Thread(target=otp_poller, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
