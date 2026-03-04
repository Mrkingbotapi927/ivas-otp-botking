import re
import requests
from urllib.parse import urljoin
import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import time
import threading

# ================= CONFIG =================
BOT_TOKEN = "8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ"
IVAS_URL = "https://ivas.tempnum.qzz.io"
IVAS_EMAIL = "iamalisindhi1122@gmail.com"
IVAS_PASSWORD = "Shoaibali@123D..king"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Global variables
user_sessions = {}      # chat_id → user data
active_numbers = {}     # number → chat_id (for auto OTP forward)
shared_session = None   # reuse login session for speed
last_otp_cache = {}     # number → last sent OTP (to avoid duplicate messages)

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
        r = session.get(login_url, timeout=30)

        m = re.search(r'name="_token" value="([^"]+)"', r.text)
        if not m:
            print("❌ CSRF token not found")
            return None
        token = m.group(1)

        payload = {
            "_token": token,
            "email": IVAS_EMAIL,
            "password": IVAS_PASSWORD
        }

        resp = session.post(login_url, data=payload, timeout=30)
        if "logout" not in resp.text.lower() and resp.status_code != 200:
            print("❌ Login failed")
            return None

        shared_session = session
        print("✅ New login successful")
        return session
    except Exception as e:
        print("Login error:", e)
        return None

# ================= FETCH COUNTRIES (Dynamic from your panel) =================
def get_countries(session):
    try:
        url = urljoin(IVAS_URL, "/portal/numbers")
        r = session.get(url, timeout=20)
        text = r.text

        # Extract possible country names (dynamic - jo bhi panel mein add karoge woh catch ho jayega)
        country_pattern = r'\b([A-Z][a-z]{3,25}(?:\s[A-Z][a-z]{3,20})?)\b'
        possible = re.findall(country_pattern, text)

        exclude = ["Login", "Dashboard", "Portal", "Numbers", "SMS", "Received", "Get", "Refresh", 
                   "Panel", "User", "Email", "Password", "Welcome", "Logout", "Home", "Active", 
                   "Expired", "Select", "Country", "Number", "Copy", "OTP", "All", "Total"]

        countries = []
        for c in possible:
            if c not in exclude and len(c) > 4 and c[0].isupper():
                countries.append(c.strip())

        countries = list(dict.fromkeys(countries))  # unique + order preserve
        if countries:
            return countries[:8]  # max 8 countries
        return ["All Countries"]
    except Exception as e:
        print("Country fetch error:", e)
        return ["All Countries"]

# ================= FETCH NUMBERS =================
def fetch_numbers(session):
    try:
        url = urljoin(IVAS_URL, "/portal/numbers")
        r = session.get(url, timeout=20)
        # 10–15 digit numbers only
        nums = re.findall(r'\b\d{10,15}\b', r.text)
        nums = list(dict.fromkeys(nums))  # remove duplicates
        return nums[:2]  # limit 2 as you wanted
    except Exception as e:
        print("Fetch numbers error:", e)
        return []

# ================= BACKGROUND AUTO OTP POLLER =================
def otp_poller():
    while True:
        time.sleep(5)  # har 5 second mein check
        if not active_numbers:
            continue

        session = get_panel_session()
        if not session:
            continue

        try:
            url = urljoin(IVAS_URL, "/portal/sms/received/getsms")
            r = session.get(url, timeout=15)
            page_text = r.text.lower()

            for number, chat_id in list(active_numbers.items()):
                if number not in page_text and number[-8:] not in page_text:
                    continue

                # Extract possible OTP (4-8 digits)
                otp_matches = re.findall(r'\b(\d{4,8})\b', r.text)
                if otp_matches:
                    latest_otp = otp_matches[-1]  # last wala mostly latest hota hai

                    # Duplicate check
                    key = f"{number}_{chat_id}"
                    if key in last_otp_cache and last_otp_cache[key] == latest_otp:
                        continue

                    last_otp_cache[key] = latest_otp

                    bot.send_message(
                        chat_id,
                        f"✅ <b>Aapki OTP aa gai hai!</b>\n\n"
                        f"📱 Number: <code>{number}</code>\n"
                        f"🔑 OTP: <code>{latest_otp}</code>\n\n"
                        f"Copy kar lo aur use kar lo 🔥",
                        parse_mode="HTML"
                    )
                    print(f"OTP forwarded to {chat_id} for {number}")
        except Exception as e:
            print("Poller error:", e)

# ================= UI =================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 Get Number")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "👋 <b>WELCOME BACK IN ALI SINDHI 👿</b>\n\n"
        "BEST TEMP NUMBER BOT\n\n"
        "🚀 Get Number dabao aur shuru ho jao!",
        reply_markup=main_menu()
    )

# ================= GET NUMBER → COUNTRIES =================
@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_number(msg):
    chat_id = msg.chat.id
    bot.send_message(chat_id, "🌍 Fetching countries from your panel...")

    session = get_panel_session()
    if not session:
        bot.send_message(chat_id, "❌ Login failed. Bot restart karo.")
        return

    countries = get_countries(session)

    kb = InlineKeyboardMarkup(row_width=2)
    for country in countries:
        kb.add(InlineKeyboardButton(f"🌍 {country}", callback_data=f"country|{country}"))

    bot.send_message(
        chat_id,
        "🌍 <b>Select Country</b>\n\nJo country aapne panel mein add ki hai usko choose karo:",
        reply_markup=kb
    )

# ================= COUNTRY SELECT → SHOW NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def select_country(call):
    chat_id = call.message.chat.id
    country = call.data.split("|", 1)[1]

    bot.answer_callback_query(call.id, f"✅ {country} selected")

    session = get_panel_session()
    if not session:
        bot.send_message(chat_id, "❌ Session expired. Get Number se shuru karo.")
        return

    numbers = fetch_numbers(session)
    if not numbers:
        bot.send_message(chat_id, "❌ No active numbers found in this country.")
        return

    # Save session & country
    user_sessions[chat_id] = {
        "session": session,
        "selected_country": country,
        "selected_number": None
    }

    kb = InlineKeyboardMarkup(row_width=2)

    for n in numbers:
        kb.add(InlineKeyboardButton(f"📋 {n}", callback_data=f"select|{n}"))

    kb.add(InlineKeyboardButton("🔄 Refresh Numbers", callback_data="refresh_nums"))
    kb.add(InlineKeyboardButton("📩 Check OTP Now", callback_data="manual_otp"))

    bot.edit_message_text(
        f"📱 <b>Numbers for {country}</b>\n\n"
        "Number choose karo ya Refresh dabao",
        chat_id,
        call.message.message_id,
        reply_markup=kb
    )

# ================= SELECT NUMBER =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("select|"))
def select_number(call):
    chat_id = call.message.chat.id
    number = call.data.split("|", 1)[1]

    if chat_id not in user_sessions:
        bot.answer_callback_query(call.id, "Session expired", show_alert=True)
        return

    user_sessions[chat_id]["selected_number"] = number
    active_numbers[number] = chat_id   # auto OTP ke liye register

    bot.answer_callback_query(call.id, f"✅ {number} selected & activated!", show_alert=True)

    bot.send_message(
        chat_id,
        f"✅ <b>Number Selected:</b> <code>{number}</code>\n\n"
        "Ab panel mein is number pe OTP aane ka wait karo.\n"
        "Jaise hi OTP aayega, main turant forward kar dunga 🔥\n\n"
        "Refresh ya Check OTP Now bhi use kar sakte ho.",
        parse_mode="HTML"
    )

# ================= REFRESH NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data == "refresh_nums")
def refresh_numbers(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id, "🔄 Refreshing...")

    session = get_panel_session(force_new=True)  # fresh for new numbers
    if not session:
        bot.send_message(chat_id, "❌ Login failed")
        return

    numbers = fetch_numbers(session)
    if not numbers:
        bot.send_message(chat_id, "❌ No numbers found")
        return

    if chat_id in user_sessions:
        user_sessions[chat_id]["session"] = session

    kb = InlineKeyboardMarkup(row_width=2)
    for n in numbers:
        kb.add(InlineKeyboardButton(f"📋 {n}", callback_data=f"select|{n}"))

    kb.add(InlineKeyboardButton("🔄 Refresh Numbers", callback_data="refresh_nums"))
    kb.add(InlineKeyboardButton("📩 Check OTP Now", callback_data="manual_otp"))

    bot.edit_message_text(
        "📱 <b>Updated Numbers</b>\n\nFresh numbers aa gaye!",
        chat_id,
        call.message.message_id,
        reply_markup=kb
    )

# ================= MANUAL OTP CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "manual_otp")
def manual_otp(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id, "🔍 Checking OTP...")

    if chat_id not in user_sessions or "selected_number" not in user_sessions[chat_id]:
        bot.send_message(chat_id, "Pehle number select karo!")
        return

    number = user_sessions[chat_id]["selected_number"]
    session = user_sessions[chat_id]["session"]

    try:
        url = urljoin(IVAS_URL, "/portal/sms/received/getsms")
        r = session.get(url, timeout=15)
        text = r.text

        if number not in text and number[-8:] not in text:
            bot.send_message(chat_id, "⏳ Abhi koi OTP nahi aaya. Thoda wait karo...")
            return

        otp_matches = re.findall(r'\b(\d{4,8})\b', text)
        if otp_matches:
            otp = otp_matches[-1]
            bot.send_message(
                chat_id,
                f"✅ <b>OTP Mil Gaya!</b>\n\n"
                f"📱 Number: <code>{number}</code>\n"
                f"🔑 OTP: <code>{otp}</code>",
                parse_mode="HTML"
            )
        else:
            bot.send_message(chat_id, "Number mila lekin OTP parse nahi hua. Panel check karo.")
    except:
        bot.send_message(chat_id, "❌ OTP check mein error. Baad mein try karo.")

# ================= START BOT & POLLER =================
if __name__ == "__main__":
    print(">> IVAS FULL AUTO BOT STARTED ✅")
    print(">> Auto OTP forwarding + Country selection ON")

    # Start background OTP poller
    poller_thread = threading.Thread(target=otp_poller, daemon=True)
    poller_thread.start()

    # Start bot
    bot.infinity_polling(skip_pending=True)
