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

user_sessions = {}      # chat_id → {'session':, 'service':, 'country':, 'number':, 'start_time':}
active_monitors = {}    # chat_id → number
shared_session = None

# ================= FLAGS =================
COUNTRY_FLAGS = {
    "Togo": "🇹🇬", "Ivory Coast": "🇨🇮", "Cote d'Ivoire": "🇨🇮", "Côte d'Ivoire": "🇨🇮",
    "Ghana": "🇬🇭", "Nigeria": "🇳🇬", "Benin": "🇧🇯", "Cameroon": "🇨🇲",
    "Kenya": "🇰🇪", "Uganda": "🇺🇬", "Tanzania": "🇹🇿", "Zambia": "🇿🇲",
    "South Africa": "🇿🇦", "Egypt": "🇪🇬", "Morocco": "🇲🇦", "Algeria": "🇩🇿",
    "India": "🇮🇳", "Pakistan": "🇵🇰", "Bangladesh": "🇧🇩", "Indonesia": "🇮🇩",
    "Philippines": "🇵🇭", "Malaysia": "🇲🇾", "Vietnam": "🇻🇳", "Thailand": "🇹🇭",
    "United States": "🇺🇸", "USA": "🇺🇸", "United Kingdom": "🇬🇧", "UK": "🇬🇧",
    "Germany": "🇩🇪", "France": "🇫🇷", "Italy": "🇮🇹", "Spain": "🇪🇸", "Brazil": "🇧🇷",
}

# ================= SESSION MANAGEMENT =================
def get_panel_session(force_new=False):
    global shared_session
    if not force_new and shared_session:
        try:
            test = shared_session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=10)
            if test.status_code == 200:
                return shared_session
        except:
            pass

    session = requests.Session()
    try:
        login_url = urljoin(IVAS_URL, "/login")
        r = session.get(login_url, timeout=25)
        m = re.search(r'name="_token" value="([^"]+)"', r.text)
        if not m:
            print("CSRF not found")
            return None
        token = m.group(1)

        payload = {"_token": token, "email": IVAS_EMAIL, "password": IVAS_PASSWORD}
        session.post(login_url, data=payload, timeout=25)
        shared_session = session
        return session
    except Exception as e:
        print("Login error:", e)
        return None

# ================= FETCH COUNTRIES (strict filter) =================
def fetch_countries(session):
    try:
        r = session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=20)
        text = r.text

        # Possible country-like strings
        candidates = re.findall(r'\b([A-Z][a-zA-Z]{3,25}(?:\s[A-Z][a-zA-Z]{3,20})?)\b', text)

        exclude_keywords = [
            "DOCTYPE", "Global", "Google", "Analytics", "Premium", "Rate", "Traffic", "Monetization",
            "Platform", "International", "Font", "Source", "Sans", "Login", "Dashboard", "Portal",
            "Numbers", "SMS", "Received", "Get", "Refresh", "Panel", "Active", "Expired", "Select",
            "Country", "Number", "Copy", "OTP", "All", "Total", "Home", "Welcome", "Logout"
        ]

        countries = []
        seen = set()
        for c in candidates:
            c = c.strip()
            if c in seen or any(kw in c for kw in exclude_keywords) or len(c) < 5:
                continue
            seen.add(c)
            countries.append(c)

        if countries:
            return sorted(list(dict.fromkeys(countries)))[:12]

        # Fallback if nothing found
        return ["Togo", "Ivory Coast", "Ghana", "Nigeria"]

    except Exception as e:
        print("Country fetch error:", e)
        return ["Togo", "Ivory Coast", "Ghana", "Nigeria"]

# ================= FETCH NUMBERS =================
def fetch_numbers(session):
    try:
        r = session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=20)
        nums = re.findall(r'(\+\d{10,15})', r.text)
        return list(dict.fromkeys(nums))[:6]
    except:
        return []

# ================= OTP POLLER =================
def otp_poller():
    while True:
        time.sleep(6)
        for chat_id, number in list(active_monitors.items()):
            if chat_id not in user_sessions:
                continue
            data = user_sessions[chat_id]
            if time.time() - data.get('start_time', 0) > 900:  # 15 min
                bot.send_message(chat_id, f"⏰ Timeout! No OTP in 15 min.\nNumber: <code>{number}</code> - Expired")
                active_monitors.pop(chat_id, None)
                continue

            session = data['session']
            try:
                r = session.get(urljoin(IVAS_URL, "/portal/sms/received/getsms"), timeout=12)
                if number not in r.text:
                    continue
                otps = re.findall(r'\b\d{4,8}\b', r.text)
                if otps:
                    otp = otps[-1]
                    bot.send_message(chat_id, f"✅ OTP aa gai!\nNumber: <code>{number}</code>\nOTP: <code>{otp}</code>")
                    active_monitors.pop(chat_id, None)
            except:
                pass

# ================= MAIN MENU =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("🚀 Get Number"))
    kb.add(KeyboardButton("🔢 Number Count"))
    kb.add(KeyboardButton("📊 My Stats"))
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "👿 WELCOME BACK IN ALI SINDHI BEST BOT", reply_markup=main_menu())

# Get Number → Service Picker
@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def service_picker(msg):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📱 WhatsApp OTP", callback_data="service|whatsapp"))
    kb.add(InlineKeyboardButton("📘 Facebook OTP", callback_data="service|facebook"))
    kb.add(InlineKeyboardButton("✈️ Telegram OTP", callback_data="service|telegram"))
    kb.add(InlineKeyboardButton("🌟 Explore Others", callback_data="service|others"))
    bot.send_message(msg.chat.id, "Choose service:", reply_markup=kb)

# Service → Countries
@bot.callback_query_handler(func=lambda c: c.data.startswith("service|"))
def show_countries(call):
    service = call.data.split("|")[1]
    chat_id = call.message.chat.id

    session = get_panel_session()
    if not session:
        bot.send_message(chat_id, "Login failed")
        return

    countries = fetch_countries(session)

    kb = InlineKeyboardMarkup(row_width=2)
    for c in countries:
        flag = COUNTRY_FLAGS.get(c, "🌍")
        kb.add(InlineKeyboardButton(f"{flag} {c}", callback_data=f"country|{service}|{c}"))

    kb.add(InlineKeyboardButton("← Back", callback_data="back|main"))

    bot.edit_message_text("🌍 Select Country", chat_id, call.message.message_id, reply_markup=kb)

# Country → Numbers
@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def show_numbers(call):
    parts = call.data.split("|")
    service = parts[1]
    country = parts[2]
    chat_id = call.message.chat.id

    session = get_panel_session(force_new=True)
    if not session:
        bot.send_message(chat_id, "Session error")
        return

    numbers = fetch_numbers(session)

    flag = COUNTRY_FLAGS.get(country, "🌍")

    kb = InlineKeyboardMarkup(row_width=1)
    for n in numbers:
        kb.add(InlineKeyboardButton(f"📱 {n}", callback_data=f"select|{service}|{country}|{n}"))

    kb.add(InlineKeyboardButton("🔄 Next Number", callback_data=f"next|{service}|{country}"))
    kb.add(InlineKeyboardButton("← Back", callback_data=f"back|service"))

    text = f"Country: {flag} {country}\nWaiting for OTP... ⏳"
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

    user_sessions[chat_id] = {
        "session": session,
        "service": service,
        "country": country,
        "start_time": time.time()
    }

# Select number
@bot.callback_query_handler(func=lambda c: c.data.startswith("select|"))
def select_number(call):
    parts = call.data.split("|")
    service = parts[1]
    country = parts[2]
    number = parts[3]
    chat_id = call.message.chat.id

    user_sessions[chat_id]["number"] = number
    active_monitors[chat_id] = number

    flag = COUNTRY_FLAGS.get(country, "🌍")
    bot.send_message(chat_id, f"Activated: {flag} {country} - {number}\nWaiting OTP...")

# Next / Refresh
@bot.callback_query_handler(func=lambda c: c.data.startswith("next|"))
def next_number(call):
    parts = call.data.split("|")
    service = parts[1]
    country = parts[2]
    chat_id = call.message.chat.id

    time.sleep(2)
    session = get_panel_session(force_new=True)
    numbers = fetch_numbers(session)

    flag = COUNTRY_FLAGS.get(country, "🌍")

    kb = InlineKeyboardMarkup(row_width=1)
    for n in numbers:
        kb.add(InlineKeyboardButton(f"📱 {n}", callback_data=f"select|{service}|{country}|{n}"))

    kb.add(InlineKeyboardButton("🔄 Next Number", callback_data=f"next|{service}|{country}"))
    kb.add(InlineKeyboardButton("← Back", callback_data=f"back|service"))

    text = f"Country: {flag} {country}\nFresh numbers loaded! Waiting OTP... ⏳"
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

# Back
@bot.callback_query_handler(func=lambda c: c.data.startswith("back|"))
def back(call):
    bot.send_message(call.message.chat.id, "Back to menu", reply_markup=main_menu())

# Other buttons
@bot.message_handler(func=lambda m: m.text == "🔢 Number Count")
def number_count(msg):
    session = get_panel_session()
    nums = fetch_numbers(session) if session else []
    bot.send_message(msg.chat.id, f"Available: {len(nums)}\n{', '.join(nums[:4])}")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def my_stats(msg):
    bot.send_message(msg.chat.id, "Stats coming soon...")

# ================= START =================
if __name__ == "__main__":
    print("Bot started")
    threading.Thread(target=otp_poller, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
