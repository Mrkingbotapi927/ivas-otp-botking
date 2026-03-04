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

user_sessions = {}      # chat_id → all data
active_monitors = {}    # chat_id → selected_number
shared_session = None

# ================= BIG FLAGS DICT (Automatic for almost all countries) =================
COUNTRY_FLAGS = {
    "Togo": "🇹🇬", "Ivory Coast": "🇨🇮", "Cote d'Ivoire": "🇨🇮", "Côte d'Ivoire": "🇨🇮",
    "Ghana": "🇬🇭", "Nigeria": "🇳🇬", "Benin": "🇧🇯", "Cameroon": "🇨🇲",
    "Liberia": "🇱🇷", "Sierra Leone": "🇸🇱", "Senegal": "🇸🇳", "Mali": "🇲🇱",
    "Kenya": "🇰🇪", "Uganda": "🇺🇬", "Tanzania": "🇹🇿", "Zambia": "🇿🇲",
    "South Africa": "🇿🇦", "Egypt": "🇪🇬", "Morocco": "🇲🇦", "Algeria": "🇩🇿",
    "India": "🇮🇳", "Pakistan": "🇵🇰", "Bangladesh": "🇧🇩", "Indonesia": "🇮🇩",
    "Philippines": "🇵🇭", "Malaysia": "🇲🇾", "Vietnam": "🇻🇳", "Thailand": "🇹🇭",
    "USA": "🇺🇸", "United States": "🇺🇸", "UK": "🇬🇧", "United Kingdom": "🇬🇧",
    "Germany": "🇩🇪", "France": "🇫🇷", "Italy": "🇮🇹", "Spain": "🇪🇸",
    "Brazil": "🇧🇷", "Mexico": "🇲🇽", "Argentina": "🇦🇷", "Colombia": "🇨🇴",
    # Add any new country here if flag missing
}

# ================= SESSION =================
def get_panel_session(force_new=False):
    global shared_session
    if not force_new and shared_session:
        try:
            if shared_session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=10).status_code == 200:
                return shared_session
        except:
            pass

    session = requests.Session()
    try:
        login_url = urljoin(IVAS_URL, "/login")
        r = session.get(login_url, timeout=25)
        m = re.search(r'name="_token" value="([^"]+)"', r.text)
        if not m:
            return None
        token = m.group(1)

        payload = {"_token": token, "email": IVAS_EMAIL, "password": IVAS_PASSWORD}
        resp = session.post(login_url, data=payload, timeout=25)

        shared_session = session
        return session
    except Exception as e:
        print("Login error:", e)
        return None

# ================= FETCH COUNTRIES (dynamic from your panel) =================
def fetch_countries(session):
    try:
        r = session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=20)
        # Better regex for real country names
        countries = re.findall(r'\b([A-Z][a-zA-Z]{3,30}(?:\s[A-Z][a-zA-Z]{3,20})?)\b', r.text)
        exclude = ["Login","Dashboard","Portal","Numbers","SMS","Received","Get","Refresh","Panel",
                   "Active","Expired","Select","Country","Number","Copy","OTP","All","Total","Home"]
        unique = list(dict.fromkeys([c.strip() for c in countries if c not in exclude and len(c) > 4]))
        return unique[:12] or ["Togo", "Ivory Coast", "Ghana", "Nigeria"]  # fallback
    except:
        return ["Togo", "Ivory Coast", "Ghana", "Nigeria"]

# ================= FETCH NUMBERS (always with +country code) =================
def fetch_numbers(session):
    try:
        r = session.get(urljoin(IVAS_URL, "/portal/numbers"), timeout=20)
        # Strict: only numbers with + (like +228.... in screenshots)
        nums = re.findall(r'(\+\d{10,15})', r.text)
        nums = list(dict.fromkeys(nums))[:6]   # max 6 like most panels
        return nums
    except Exception as e:
        print("Fetch numbers error:", e)
        return []

# ================= BACKGROUND OTP POLLER =================
def otp_poller():
    while True:
        time.sleep(5)
        for chat_id, number in list(active_monitors.items()):
            if chat_id not in user_sessions:
                continue
            data = user_sessions[chat_id]
            if time.time() - data.get('start_time', 0) > 900:   # 15 minutes timeout
                bot.send_message(chat_id, f"⏰ Timeout! No OTP received within 15 minutes.\n\nNumber status:\n<code>{number}</code> - Expired")
                if chat_id in active_monitors:
                    del active_monitors[chat_id]
                continue

            session = data['session']
            try:
                r = session.get(urljoin(IVAS_URL, "/portal/sms/received/getsms"), timeout=12)
                if number not in r.text:
                    continue
                otps = re.findall(r'\b(\d{4,8})\b', r.text)
                if otps:
                    otp = otps[-1]
                    bot.send_message(
                        chat_id,
                        f"✅ <b>Aapki OTP aa gai hai!</b>\n\n"
                        f"📱 Number: <code>{number}</code>\n"
                        f"🔑 OTP: <code>{otp}</code>\n\nCopy kar lo aur use kar lo 🔥",
                        parse_mode="HTML"
                    )
                    if chat_id in active_monitors:
                        del active_monitors[chat_id]
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
    bot.send_message(msg.chat.id, "👿 <b>WELCOME BACK IN ALI SINDHI BEST NUMBERS BOT</b>\n\n🚀 Get Number dabao!", reply_markup=main_menu())

# ================= GET NUMBER → SERVICE PICKER =================
@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def service_picker(msg):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📱 WhatsApp OTP", callback_data="service|whatsapp"))
    kb.add(InlineKeyboardButton("📘 Facebook OTP", callback_data="service|facebook"))
    kb.add(InlineKeyboardButton("✈️ Telegram OTP", callback_data="service|telegram"))
    kb.add(InlineKeyboardButton("🌟 Explore Others", callback_data="service|others"))
    bot.send_message(msg.chat.id, "🔍 <b>Service Picker</b>\nChoose where you want numbers from:", reply_markup=kb)

# ================= SERVICE → COUNTRIES (with flags) =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("service|"))
def show_countries(call):
    service = call.data.split("|")[1]
    chat_id = call.message.chat.id

    session = get_panel_session()
    if not session:
        bot.send_message(chat_id, "❌ Login failed")
        return

    countries = fetch_countries(session)

    kb = InlineKeyboardMarkup(row_width=2)
    for country in countries:
        flag = COUNTRY_FLAGS.get(country, COUNTRY_FLAGS.get(country.replace("Cote", "Ivory").replace("Côte", "Ivory"), "🌍"))
        kb.add(InlineKeyboardButton(f"{flag} {country}", callback_data=f"country|{service}|{country}"))

    kb.add(InlineKeyboardButton("← Back", callback_data="back|main"))

    bot.edit_message_text(
        f"🌍 <b>Select Country</b>\n{SERVICE_EMOJIS.get(service, service.capitalize())}",
        chat_id, call.message.message_id, reply_markup=kb
    )

# ================= COUNTRIES → NUMBERS LIST (with +code & Next Number) =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def show_numbers(call):
    parts = call.data.split("|")
    service = parts[1]
    country = parts[2]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "Fetching fresh numbers...")

    session = get_panel_session(force_new=False)
    if not session:
        bot.send_message(chat_id, "❌ Session expired")
        return

    numbers = fetch_numbers(session)

    flag = COUNTRY_FLAGS.get(country, COUNTRY_FLAGS.get(country.replace("Cote", "Ivory").replace("Côte", "Ivory"), "🌍"))

    kb = InlineKeyboardMarkup(row_width=1)
    for num in numbers:
        kb.add(InlineKeyboardButton(f"📱 {num}", callback_data=f"select|{service}|{country}|{num}"))

    kb.add(InlineKeyboardButton("🔄 Next Number", callback_data=f"next|{service}|{country}"))
    kb.add(InlineKeyboardButton("← Back", callback_data=f"back|country|{service}"))

    text = f"Country: {flag} {country}\nService: {SERVICE_EMOJIS.get(service, service)}\nWaiting for OTP...... ⏳"

    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

    user_sessions[chat_id] = {
        "session": session,
        "service": service,
        "country": country,
        "start_time": time.time()
    }

# ================= SELECT NUMBER =================
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
    bot.answer_callback_query(call.id, f"✅ {number} activated!", show_alert=True)

    bot.send_message(
        chat_id,
        f"✅ <b>Number Selected & Activated</b>\n\n"
        f"Country: {flag} {country}\n"
        f"Number: <code>{number}</code>\n\n"
        f"Waiting for OTP... ⏳\n(15 min timeout)\n\n"
        f"Jaise hi panel mein OTP aayega, main turant forward kar dunga!",
        parse_mode="HTML"
    )

# ================= NEXT NUMBER (Refresh + Fresh Numbers) =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("next|"))
def next_number(call):
    parts = call.data.split("|")
    service = parts[1]
    country = parts[2]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "🔄 Getting fresh numbers...")

    # Force new session + small delay so panel gives new numbers
    time.sleep(3)
    session = get_panel_session(force_new=True)

    if not session:
        bot.send_message(chat_id, "❌ Login failed")
        return

    numbers = fetch_numbers(session)

    flag = COUNTRY_FLAGS.get(country, "🌍")

    kb = InlineKeyboardMarkup(row_width=1)
    for num in numbers:
        kb.add(InlineKeyboardButton(f"📱 {num}", callback_data=f"select|{service}|{country}|{num}"))

    kb.add(InlineKeyboardButton("🔄 Next Number", callback_data=f"next|{service}|{country}"))
    kb.add(InlineKeyboardButton("← Back", callback_data=f"back|country|{service}"))

    text = f"Country: {flag} {country}\nService: {SERVICE_EMOJIS.get(service, service)}\nWaiting for OTP...... ⏳\n\n✅ Fresh numbers loaded!"

    if call.message:
        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)

    if chat_id in user_sessions:
        user_sessions[chat_id]["session"] = session

# ================= BACK BUTTONS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("back|"))
def back_handler(call):
    bot.answer_callback_query(call.id, "Back...")
    if "main" in call.data:
        bot.send_message(call.message.chat.id, "Main menu", reply_markup=main_menu())
    else:
        # simple back to service picker
        service_picker(call.message)

# ================= NUMBER COUNT & MY STATS =================
@bot.message_handler(func=lambda m: m.text == "🔢 Number Count")
def number_count(msg):
    session = get_panel_session()
    nums = fetch_numbers(session) if session else []
    bot.send_message(msg.chat.id, f"🔢 <b>Available Numbers:</b> {len(nums)}\n\nFresh numbers: {nums[:3]}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def my_stats(msg):
    bot.send_message(msg.chat.id, "📊 <b>Your Stats</b>\n\nTotal Numbers Used: 0\nSuccessful OTPs: 0\nComing soon more stats 🔥", parse_mode="HTML")

# ================= SERVICE EMOJIS =================
SERVICE_EMOJIS = {
    "whatsapp": "📱 WhatsApp OTP",
    "facebook": "📘 Facebook OTP",
    "telegram": "✈️ Telegram OTP",
    "others": "🌟 Explore Others",
}

# ================= START BOT =================
if __name__ == "__main__":
    print(">> ALI SINDHI BOT STARTED - Full WhatsApp Style ✅")
    print(">> Auto flags + Next Number working + Auto OTP forward")

    poller_thread = threading.Thread(target=otp_poller, daemon=True)
    poller_thread.start()

    bot.infinity_polling(skip_pending=True)
