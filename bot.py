=========================================

IVAS Dynamic OTP Bot (Auto Country)

=========================================

Features:

- Auto fetch numbers from IVAS panel

- Dynamic country keyboard

- Clean country names

- Works on Railway

=========================================

import os import re import asyncio import requests from collections import defaultdict

from telegram import ReplyKeyboardMarkup, KeyboardButton, Update from telegram.ext import ( Application, CommandHandler, MessageHandler, ContextTypes, filters, )

BOT_TOKEN = os.getenv("8521079986:AAGBGaW21GlBOTTbvjnZSlp78_bvIVn5RTQ") IVAS_EMAIL = os.getenv("iamalisindhi1122@gmail.com") IVAS_PASSWORD = os.getenv("Shoaibali@123D..king")

=============================

Helpers

=============================

def clean_country(name: str) -> str: """Remove trailing numeric codes from IVAS country.""" if not name: return "" return re.sub(r"\s+\d+$", "", name).strip()

def extract_countries(rows): countries = set() for r in rows: c = r.get("country", "").strip() if c: countries.add(c) return sorted(list(countries))

def build_country_keyboard(countries): keyboard = [] row = []

for c in countries:
    row.append(KeyboardButton(c))
    if len(row) == 2:
        keyboard.append(row)
        row = []

if row:
    keyboard.append(row)

keyboard.append([KeyboardButton("🔙 Back")])

return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

=============================

IVAS FETCH (HTTP VERSION)

=============================

def fetch_numbers_from_ivas(): """ Replace URLs below with your real IVAS endpoints if different. This function returns list of: { country: str, number: str } """

try:
    session = requests.Session()

    # -------- LOGIN --------
    login_url = "https://portal.ivasms.com/login"
    session.post(
        login_url,
        data={"email": IVAS_EMAIL, "password": IVAS_PASSWORD},
        timeout=30,
    )

    # -------- FETCH NUMBERS --------
    numbers_url = "https://portal.ivasms.com/test-system"
    resp = session.get(numbers_url, timeout=30)
    html = resp.text

    # ===== SIMPLE PARSER =====
    # NOTE: adjust regex if IVAS HTML changes

    pattern = re.compile(
        r"<tr>.*?<td>(.*?)</td>.*?<td>(\d+)</td>", re.S
    )

    rows = []
    for match in pattern.findall(html):
        raw_country, number = match

        country = clean_country(raw_country)

        rows.append(
            {
                "country": country,
                "number": number,
            }
        )

    return rows

except Exception as e:
    print("IVAS fetch error:", e)
    return []

=============================

Telegram Handlers

=============================

MAIN_KEYBOARD = ReplyKeyboardMarkup( [ [KeyboardButton("🚀 Get Number")], [KeyboardButton("⚙️ Number Count"), KeyboardButton("📈 My Stats")], ], resize_keyboard=True, )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data["count"] = context.user_data.get("count", 2)

await update.message.reply_text(
    "✨ OTP Dashboard is ready\n"
    "🚀 Get Number: fetch fresh numbers\n"
    "⚙️ Number Count: set your batch size\n"
    "📈 My Stats: view today's activity\n\n"
    f"📌 Current setting: {context.user_data['count']} number(s)",
    reply_markup=MAIN_KEYBOARD,
)

=============================

GET NUMBER

=============================

async def handle_get_number(update: Update, context: ContextTypes.DEFAULT_TYPE): msg = await update.message.reply_text("🔄 Fetching numbers...")

rows = await asyncio.to_thread(fetch_numbers_from_ivas)

if not rows:
    await msg.edit_text("❌ Failed to get numbers. Please try again.")
    return

# save all rows
context.user_data["all_rows"] = rows

countries = extract_countries(rows)

if not countries:
    await msg.edit_text("❌ No countries found.")
    return

keyboard = build_country_keyboard(countries)

await msg.edit_text(
    "📱 WHATSAPP - Select Country:",
    reply_markup=keyboard,
)

=============================

COUNTRY SELECT

=============================

async def handle_country(update: Update, context: ContextTypes.DEFAULT_TYPE): text = update.message.text

if text == "🔙 Back":
    await start(update, context)
    return

rows = context.user_data.get("all_rows", [])
count = context.user_data.get("count", 2)

# filter by country
filtered = [r for r in rows if r["country"] == text]

if not filtered:
    await update.message.reply_text("❌ No numbers for this country.")
    return

selected = filtered[:count]

keyboard = []
for item in selected:
    keyboard.append([KeyboardButton(f"📱 +{item['number']}")])

keyboard.append([KeyboardButton("🔄 Next Number")])
keyboard.append([KeyboardButton("🔙 Back")])

await update.message.reply_text(
    f"Country: {text}\nService: WhatsApp\nWaiting for OTP... ⏳",
    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
)

=============================

NUMBER COUNT

=============================

async def handle_count(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Send number count (e.g., 2, 5, 10)") context.user_data["awaiting_count"] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE): text = update.message.text

# count setter
if context.user_data.get("awaiting_count"):
    if text.isdigit():
        context.user_data["count"] = int(text)
        context.user_data["awaiting_count"] = False

        await update.message.reply_text(
            f"✅ Number count set to {text}", reply_markup=MAIN_KEYBOARD
        )
        return

# route buttons
if text == "🚀 Get Number":
    await handle_get_number(update, context)
elif text == "⚙️ Number Count":
    await handle_count(update, context)
elif text == "📈 My Stats":
    await update.message.reply_text("📊 Stats coming soon...")
else:
    # maybe country click
    await handle_country(update, context)

=============================

MAIN

=============================

def main(): print(">> IVAS HTTP BOT STARTED")

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()

if name == "main": main()
