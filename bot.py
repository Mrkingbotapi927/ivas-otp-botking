import telebot
from telebot import types
import os
import sqlite3
import time
import threading
import re
from playwright.sync_api import sync_playwright

# ================= CONFIG =================
API_TOKEN = "8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ"
SUPER_OWNER_ID = 8382316368

IVAS_EMAIL = "iamalisindhi1122@gmail.com"
IVAS_PASSWORD = "Shoaibali@123D..king"
IVAS_URL = "https://ivas.tempnum.qzz.io/portal/live/my_sms"

bot = telebot.TeleBot(API_TOKEN)

# ================= KEYBOARDS =================
main_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.row("🚀 Get Number")
main_kb.row("📊 My Stats")

def service_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💬 WhatsApp OTP", callback_data="svc_whatsapp"),
        types.InlineKeyboardButton("👥 Facebook OTP", callback_data="svc_facebook"),
        types.InlineKeyboardButton("✈️ Telegram OTP", callback_data="svc_telegram"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="svc_refresh"),
    )
    return kb

# ================= UTILS =================
def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

# ================= IVAS FETCH =================
def fetch_ivas_numbers(service=None):
    numbers = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            page.goto(IVAS_URL, timeout=60000)

            # login
            page.fill('input[type="email"]', IVAS_EMAIL)
            page.fill('input[type="password"]', IVAS_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # open SMS page
            try:
                page.goto(f"{IVAS_URL}/portal/sms", timeout=60000)
                page.wait_for_timeout(3000)
            except:
                pass

            body = page.locator("body").inner_text()
            found = re.findall(r'\+?\d{9,15}', body)

            seen = set()
            for num in found:
                if num not in seen:
                    seen.add(num)
                    numbers.append(num)

            browser.close()

    except Exception as e:
        print("IVAS fetch error:", e)

    return numbers[:12]

# ================= WATCHER =================
def ivas_watcher():
    print(">> IVAS WATCHER STARTED")
    last_otp = ""

    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page()
                page.goto(IVAS_URL, timeout=60000)

                page.fill('input[type="email"]', IVAS_EMAIL)
                page.fill('input[type="password"]', IVAS_PASSWORD)
                page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle")

                print(">> IVAS LOGIN OK")

                while True:
                    try:
                        page.click("text=Get SMS")
                        page.wait_for_timeout(3000)
                        body = page.locator("body").inner_text()

                        if "You do not have any SMS" not in body:
                            otp = extract_otp(body)
                            if otp and otp != last_otp:
                                last_otp = otp
                                bot.send_message(SUPER_OWNER_ID, f"📩 IVAS OTP: {otp}")
                    except Exception as e:
                        print("IVAS loop error:", e)

                    time.sleep(5)

        except Exception as e:
            print("IVAS restart:", e)
            time.sleep(10)

# ================= HANDLERS =================
@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.send_message(m.chat.id, "✨ OTP Dashboard is ready", reply_markup=main_kb)

@bot.message_handler(func=lambda m: m.text == "🚀 Get Number")
def get_number(m):
    bot.send_message(
        m.chat.id,
        "🧭 Service Picker\nChoose where you want numbers from:",
        reply_markup=service_keyboard()
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("svc_"))
def show_numbers(c):
    bot.answer_callback_query(c.id)
    msg = bot.send_message(c.message.chat.id, "⏳ Fetching numbers from IVAS...")

    nums = fetch_ivas_numbers()

    if not nums:
        bot.edit_message_text("❌ No active numbers found",
                              c.message.chat.id,
                              msg.message_id)
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    for n in nums:
        kb.add(types.InlineKeyboardButton(n, callback_data=f"num_{n}"))

    bot.edit_message_text(
        "📱 Available Numbers:",
        c.message.chat.id,
        msg.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("num_"))
def number_selected(c):
    bot.answer_callback_query(c.id)
    number = c.data.split("_", 1)[1]

    bot.send_message(
        c.message.chat.id,
        f"✅ Number selected:\n📱 {number}\n\n⏳ Waiting for OTP..."
    )

# ================= BOOT =================
threading.Thread(target=ivas_watcher, daemon=True).start()

print(">> SYSTEM ONLINE")
bot.infinity_polling()
