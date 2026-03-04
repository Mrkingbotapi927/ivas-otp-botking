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

# Global
shared_session = None
target_group_id = None
owner_chat_id = None

# Country code → name + flag (sirf common OTP wale + tumhare panel ke)
COUNTRY_CODES = {
    "92":  ("Pakistan",      "🇵🇰"),
    "225": ("Ivory Coast",   "🇨🇮"),
    "228": ("Togo",          "🇹🇬"),
    "233": ("Ghana",         "🇬🇭"),
    "234": ("Nigeria",       "🇳🇬"),
    "263": ("Zimbabwe",      "🇿🇼"),
    "7":   ("Kazakhstan",    "🇰🇿"),
    "41":  ("Switzerland",   "🇨🇭"),
    "1":   ("USA/Canada",    "🇺🇸"),
    "44":  ("United Kingdom","🇬🇧"),
    "91":  ("India",         "🇮🇳"),
    "880": ("Bangladesh",    "🇧🇩"),
    "62":  ("Indonesia",     "🇮🇩"),
    "63":  ("Philippines",   "🇵🇭"),
    "66":  ("Thailand",      "🇹🇭"),
    "84":  ("Vietnam",       "🇻🇳"),
    "60":  ("Malaysia",      "🇲🇾"),
}

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

# ================= FETCH ALL NUMBERS FROM MY NUMBERS PAGE =================
def fetch_all_numbers(session):
    try:
        r = session.get(urljoin(IVAS_URL, "/my-numbers"), timeout=20)
        if r.status_code != 200:
            r = session.get(urljoin(IVAS_URL, "/client/my-numbers"), timeout=20)
        text = r.text

        # 10-15 digit numbers (with or without +)
        nums = re.findall(r'(?:\+)?(\d{10,15})', text)
        nums = list(dict.fromkeys(nums))  # unique
        return nums[:100]  # limit
    except Exception as e:
        print("Fetch error:", e)
        return []

# ================= GROUP NUMBERS BY COUNTRY (only added ones) =================
def group_numbers_by_country(numbers):
    groups = {}
    for num in numbers:
        clean = num.lstrip('+')
        matched = False
        for code, (country, flag) in COUNTRY_CODES.items():
            if clean.startswith(code):
                if country not in groups:
                    groups[country] = []
                groups[country].append(num if num.startswith('+') else '+' + num)
                matched = True
                break
        if not matched:
            # Agar koi unknown country code ho to "Other" mein daal do
            if "Other" not in groups:
                groups["Other"] = []
            groups["Other"].append(num if num.startswith('+') else '+' + num)
    return groups

# ================= MAIN MENU =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("🚀 Get Number"))
    kb.add(KeyboardButton("🔄 Refresh Panel"))
    kb.add(KeyboardButton("📍 Set OTP Group"))
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    global owner_chat_id
    owner_chat_id = msg.chat.id
    bot.send_message(msg.chat.id, "👿 ALI SINDHI BOT READY\nSirf panel mein add kiye countries dikhege", reply_markup=main_menu())

# ================= GET NUMBER → ONLY PANEL COUNTRIES =================
@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_countries_handler(msg):
    session = get_panel_session(force_new=True)
    if not session:
        bot.send_message(msg.chat.id, "❌ Login failed")
        return

    numbers = fetch_all_numbers(session)
    if not numbers:
        bot.send_message(msg.chat.id, "❌ Panel mein abhi koi number add nahi hai")
        return

    groups = group_numbers_by_country(numbers)
    if not groups:
        bot.send_message(msg.chat.id, "❌ Koi country match nahi mila (new country code add karna padega)")
        return

    kb = InlineKeyboardMarkup(row_width=2)
    for country in sorted(groups.keys()):
        flag = next((f for c, f in COUNTRY_CODES.values() if c == country), "🌍")
        kb.add(InlineKeyboardButton(f"{flag} {country}", callback_data=f"country|{country}"))

    bot.send_message(msg.chat.id, "🌍 Select Country (Sirf panel mein added)", reply_markup=kb)

# ================= COUNTRY CLICK → SHOW NUMBERS + COPY =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def show_numbers_handler(call):
    country = call.data.split("|")[1]
    chat_id = call.message.chat.id

    session = get_panel_session()
    numbers = fetch_all_numbers(session)
    groups = group_numbers_by_country(numbers)

    country_nums = groups.get(country, [])
    if not country_nums:
        bot.edit_message_text(f"No numbers for {country}", chat_id, call.message.message_id)
        return

    flag = next((f for c, f in COUNTRY_CODES.values() if c == country), "🌍")

    kb = InlineKeyboardMarkup(row_width=1)
    for num in country_nums[:8]:  # max 8 dikha rahe hain
        kb.add(InlineKeyboardButton(f"📱 {num}", callback_data=f"copy|{num}"))

    if len(country_nums) > 8:
        kb.add(InlineKeyboardButton("🔄 More", callback_data=f"more|{country}"))

    kb.add(InlineKeyboardButton("← Back", callback_data="back"))

    text = f"{flag} {country}\n\nNumbers:\nClick to copy (silent)"
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=kb)

# ================= SILENT COPY =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("copy|"))
def silent_copy_handler(call):
    number = call.data.split("|", 1)[1]
    bot.answer_callback_query(call.id, "Copied!", show_alert=False)
    # Koi message nahi bhejna

# ================= MORE NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("more|"))
def more_numbers_handler(call):
    country = call.data.split("|")[1]
    show_numbers_handler(call)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back_handler(call):
    bot.answer_callback_query(call.id, "Back...")
    bot.send_message(call.message.chat.id, "Main menu", reply_markup=main_menu())

# ================= SET OTP GROUP =================
@bot.message_handler(func=lambda m: m.text == "📍 Set OTP Group")
def set_otp_group(msg):
    global target_group_id
    target_group_id = msg.chat.id
    bot.send_message(msg.chat.id, f"✅ OTP Group Set!\nGroup ID: {target_group_id}")

# ================= REFRESH =================
@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Panel")
def refresh_panel(msg):
    bot.send_message(msg.chat.id, "🔄 Panel se latest numbers le rahe hain...")
    get_countries_handler(msg)

# ================= OTP POLLER =================
def otp_poller():
    global target_group_id, owner_chat_id
    while True:
        time.sleep(10)
        if not target_group_id or not owner_chat_id:
            continue

        session = get_panel_session()
        if not session:
            continue

        try:
            r = session.get(urljoin(IVAS_URL, "/sms-test-history"), timeout=15)
            text = r.text
            otps = re.findall(r'\b\d{4,8}\b', text)
            for otp in otps:
                if otp not in last_seen:
                    last_seen.add(otp)
                    bot.send_message(target_group_id, f"📩 New OTP: <code>{otp}</code>", parse_mode="HTML")
                    bot.send_message(owner_chat_id, "✅ Aapki OTP chat group mein receive ho gai hai 🔥")
        except:
            pass

# ================= START =================
if __name__ == "__main__":
    print(">> ALI SINDHI iVAS BOT STARTED ✅")
    print(">> Sirf panel mein add kiye countries dikhege")

    threading.Thread(target=otp_poller, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
