from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import requests
import sqlite3
import random
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
from telegram.error import Forbidden


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TOKEN")
CMC_API_KEY = os.getenv("CMC_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

PRICE_EUR = 14.99

random_names = [
    "Gabija 🔞", "Emilija 🔞", "Austėja 🔞", "Ugnė 🔞", "Ieva 🔞",
    "Viktorija 🔞", "Greta 🔞", "Karolina 🔞", "Monika 🔞", "Eglė 🔞",
    "Rugilė 🔞", "Kamilė 🔞", "Gabrielė 🔞", "Paulina 🔞", "Justė 🔞",
    "Gintarė 🔞", "Miglė 🔞", "Aistė 🔞", "Agnė 🔞", "Laura 🔞",
    "Simona 🔞", "Erika 🔞", "Kristina 🔞", "Rūta 🔞", "Indrė 🔞",
    "Akvilė 🔞", "Augustė 🔞", "Kotryna 🔞", "Patricija 🔞", "Liepa 🔞",
    "Luknė 🔞", "Amelija 🔞", "Elzė 🔞", "Smiltė 🔞", "Saulė 🔞",
    "Viltė 🔞", "Milėja 🔞", "Adrija 🔞", "Danielė 🔞", "Ema 🔞",
    "Meda 🔞", "Neringa 🔞", "Vaida 🔞", "Inga 🔞", "Dovilė 🔞",
    "Jurgita 🔞", "Renata 🔞", "Sandra 🔞", "Rasa 🔞", "Lina 🔞",
    "Giedrė 🔞", "Daiva 🔞", "Edita 🔞", "Aurelija 🔞", "Vilma 🔞",
    "Raminta 🔞", "Deimantė 🔞", "Dominyka 🔞", "Julija 🔞", "Marija 🔞",
    "Sofija 🔞", "Adelė 🔞", "Barbora 🔞", "Elena 🔞", "Olivija 🔞",
    "Tėja 🔞", "Vakarė 🔞", "Jorė 🔞", "Rusnė 🔞", "Urtė 🔞",
    "Ariana 🔞", "Beatričė 🔞", "Diana 🔞", "Elžbieta 🔞", "Fausta 🔞",
    "Gerda 🔞", "Ignė 🔞", "Jolanta 🔞", "Kornelija 🔞", "Liveta 🔞",
    "Margarita 🔞", "Natalija 🔞", "Odeta 🔞", "Roberta 🔞", "Silvija 🔞",
    "Toma 🔞", "Valerija 🔞", "Evita 🔞"
]

bielkos_videku_id = []


# ============================================================
# DATABASE
# ============================================================

# Railway persistent volume is mounted at /data
# If running locally, use users.db instead.
if os.path.exists("/data"):
    DB_PATH = "/data/users.db"
else:
    DB_PATH = "users.db"


db = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'video'
)
""")


# Upgrade an existing database that doesn't have media_type yet.
# All previously saved items are videos, so they get "video".
try:
    cursor.execute("""
        ALTER TABLE videos
        ADD COLUMN media_type TEXT NOT NULL DEFAULT 'video'
    """)
except sqlite3.OperationalError:
    # Column already exists
    pass


db.commit()


# ============================================================
# CRYPTO PRICE
# ============================================================

def get_crypto_amount(symbol):

    url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accepts": "application/json"
    }

    params = {
        "symbol": symbol,
        "convert": "EUR"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    price_eur = data["data"][symbol][0]["quote"]["EUR"]["price"]

    return PRICE_EUR / price_eur


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Save user
    cursor.execute(
        "INSERT OR IGNORE INTO users (chat_id) VALUES (?)",
        (update.effective_chat.id,)
    )

    db.commit()

    username = (
        f"@{update.effective_user.username}"
        if update.effective_user.username
        else "User"
    )

    message = f"""👋 Sveikas, {username}!

Šita vieta ne kiekvienam. Čia susirenka vyrai, kuriems patinka atviresnis turinys, drąsesnės temos ir dalykai, apie kuriuos viešai ne visada kalbama.

🎥 Lietuviškas turinys ir privati medžiaga, kurios viešai nepamatysi. 😉
💬 Jokių bereikalingų kalbų – atvira vyrų bendruomenė ir temos, kurios iš tikrųjų domina.
👀 Jei supranti, apie ką čia, turbūt ilgai aiškinti nereikia.

⸻

💳 {username}, pasirink mokėjimo planą (tai ne automatinė prenumerata) ir atsiskaitymo būdą, kad gautum pilną prieigą prie privataus turinio ir diskusijų."""

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 MĖNESIO NARYSTĖ: 14.99€ CRYPTO",
                callback_data="mokejimas"
            )
        ]
    ]

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# HOURLY MEDIA
# ============================================================

async def hourly_video(context: ContextTypes.DEFAULT_TYPE):

    # Always use Lithuanian time, regardless of server location/timezone
    lithuania_tz = ZoneInfo("Europe/Vilnius")
    now = datetime.now(lithuania_tz)

    print(f"Hourly job triggered. Lithuanian time: {now:%Y-%m-%d %H:%M:%S}")

    # Don't send media between 00:00 and 08:00 Lithuanian time
    if 0 <= now.hour < 8:
        print("Night time in Lithuania - skipping media.")
        return

    print("Sending hourly media...")

    cursor.execute(
        "SELECT id, file_id, media_type FROM videos"
    )

    videos = cursor.fetchall()

    if not videos:
        print("No media available.")
        return

    media_id, file_id, media_type = random.choice(videos)

    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()

    for (chat_id,) in users:

        try:

            randname = random.choice(random_names)

            if media_id in bielkos_videku_id:
                randname = "Gerda 🔞"

            caption = f"""{randname}
Pilnas video TIK mūsų grupėje‼️ 😎

<b>TIK VYRAMS 🔑</b> grupėje daugiau kaip <b>64 000 lietuviškų 🔞 failų</b>, ir ji kasdien pildoma nauju turiniu. 📼

<b>TIK VYRAMS 🔑</b> – tai privati ir unikali „Telegram“ bendruomenė, kurioje dalijamės lietuvišku OnlyFans turiniu, Snapchat įrašais, įvairiais archyvais ir daugiau. Taip pat kalbame apie laisvai prieinamas merginas, dalinamės snapchat kontaktais bei aptariame tinder pasimatymų užkulisius.

🎯 Visa medžiaga – tik lietuviška. Jokio užsienietiško turinio.

<b>Nori prisijungti?</b>
Spausk čia 👉 <b>/START</b>"""

            # Send a photo if the saved item is a photo
            if media_type == "photo":

                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML"
                )

            # Otherwise send it as a video
            else:

                await context.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=caption,
                    parse_mode="HTML"
                )

        except Forbidden:

            # User blocked the bot / bot cannot contact them anymore
            print(
                f"User {chat_id} blocked the bot. "
                f"Removing from database."
            )

            cursor.execute(
                "DELETE FROM users WHERE chat_id = ?",
                (chat_id,)
            )

            db.commit()

        except Exception as e:

            # Keep user in DB for temporary/network/Telegram errors
            print(f"Failed to send to {chat_id}: {e}")


# ============================================================
# /ADDVIDEO
# Accepts BOTH photos and videos
# ============================================================

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("add media")

    # Admin only
    if update.effective_user.id != ADMIN_ID:
        print("not admin")
        print(update.effective_user.id)
        return

    # Must reply to a message
    if not update.message.reply_to_message:

        await update.message.reply_text(
            "❌ Reply to a video or photo with /addvideo"
        )

        return

    replied_message = update.message.reply_to_message

    # Check if it's a video
    if replied_message.video:

        file_id = replied_message.video.file_id
        media_type = "video"

    # Check if it's a photo
    elif replied_message.photo:

        # Telegram gives several image sizes.
        # Last one is normally the highest quality.
        file_id = replied_message.photo[-1].file_id
        media_type = "photo"

    else:

        await update.message.reply_text(
            "❌ The message you're replying to doesn't contain a video or photo."
        )

        return

    # Save Telegram file_id + media type
    cursor.execute(
        "INSERT INTO videos (file_id, media_type) VALUES (?, ?)",
        (file_id, media_type)
    )

    db.commit()

    media_id = cursor.lastrowid

    await update.message.reply_text(
        f"✅ {media_type.capitalize()} added!\n\nID: {media_id}"
    )


# ============================================================
# /VIDEOS
# ============================================================

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("LIST")

    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT id, media_type FROM videos ORDER BY id"
    )

    videos = cursor.fetchall()

    if not videos:

        await update.message.reply_text(
            "📭 No media saved."
        )

        return

    message = "🎥 Saved media:\n\n"

    for media_id, media_type in videos:

        if media_type == "photo":
            emoji = "🖼️"
        else:
            emoji = "🎥"

        message += f"{emoji} ID: {media_id} ({media_type})\n"

    message += "\nDelete with /deletevideo ID"

    await update.message.reply_text(message)


# ============================================================
# /DELETEVIDEO
# ============================================================

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "Usage:\n/deletevideo ID"
        )

        return

    try:

        media_id = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ ID must be a number."
        )

        return

    cursor.execute(
        "DELETE FROM videos WHERE id = ?",
        (media_id,)
    )

    db.commit()

    if cursor.rowcount == 0:

        await update.message.reply_text(
            "❌ Media not found."
        )

    else:

        await update.message.reply_text(
            f"🗑️ Media {media_id} deleted."
        )


# ============================================================
# /USERS
# ============================================================

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    count = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👥 Stored users: {count}"
    )


# ============================================================
# /TESTVIDEO
# ============================================================

async def test_video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT id, file_id, media_type FROM videos"
    )

    videos = cursor.fetchall()

    if not videos:

        await update.message.reply_text(
            "❌ No media saved."
        )

        return

    media_id, file_id, media_type = random.choice(videos)

    if media_type == "photo":

        await update.message.reply_photo(
            photo=file_id,
            caption=f"🧪 Test photo\nID: {media_id}"
        )

    else:

        await update.message.reply_video(
            video=file_id,
            caption=f"🧪 Test video\nID: {media_id}"
        )


# ============================================================
# BUTTONS
# ============================================================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    # --------------------------------------------------------
    # CHECK PAYMENT
    # --------------------------------------------------------

    if query.data == "checkpayment":

        await asyncio.sleep(random.uniform(0.3, 3))

        msg = """Mokėjimas dar negautas, prašome patikrinti vėliau."""

        await query.message.reply_text(
            msg,
            parse_mode="Markdown"
        )

        return

    # --------------------------------------------------------
    # PAYMENT OPTIONS
    # --------------------------------------------------------

    if query.data == "mokejimas":

        keyboard = [
            [
                InlineKeyboardButton("$SOL", callback_data="sol"),
                InlineKeyboardButton("$ETH", callback_data="eth"),
                InlineKeyboardButton("$USDT", callback_data="usdt"),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Grįžti",
                    callback_data="back"
                )
            ]
        ]

        msg = """💳 Mėnesio narystė

📅 Trukmė 1 mėnuo
💰 Kaina 14,99 €
⏳ Narystė galios 30 dienų nuo apmokėjimo patvirtinimo.

Kaip atsiskaityti:
1️⃣ Pasirink norimą kriptovaliutą.
2️⃣ Nukopijuok pateiktą mokėjimo adresą.
3️⃣ Išsiųsk tiksliai nurodytą sumą į pateiktą adresą.
4️⃣ Palauk, kol mokėjimas bus patvirtintas.

⚠️ Įsitikink, kad siunčiama suma yra visiškai tiksli. Mokėjimo patvirtinimas gali užtrukti iki 30 minučių.

👇 Pasirink kriptovaliutą atsiskaitymui:"""

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # --------------------------------------------------------
    # CRYPTO PAYMENT
    # --------------------------------------------------------

    if query.data in ["sol", "eth", "usdt"]:

        crypto_info = {

            "sol": {
                "symbol": "SOL",
                "name": "SOLANA",
                "network": "Solana",
                "address": "3en3sLwfQ5d4RNUKWa2aLhhhmEmXYg8rMv5kbA6dUPKN"
            },

            "eth": {
                "symbol": "ETH",
                "name": "ETHEREUM",
                "network": "Ethereum",
                "address": "0x015B97f6fD04A16B1790d3F0BE1567334a72812b"
            },

            "usdt": {
                "symbol": "USDT",
                "name": "USDT",
                "network": "TRC20",
                "address": "TBJbSEnGZg5HjLpk72TxGNWkGGyevkFzM4"
            }

        }

        coin = crypto_info[query.data]

        try:

            amount = get_crypto_amount(
                coin["symbol"]
            )

            amount = str(amount)[:6]

            keyboard = [
                [
                    InlineKeyboardButton(
                        "Patikrinti mokėjimą",
                        callback_data="checkpayment"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Grįžti",
                        callback_data="mokejimas"
                    )
                ]
            ]

            msg = f"""💳 {coin["name"]} pavedimas

🏦 Adresas: (Paspausk, kad nukopijuotum)
{coin["address"]}

⚡ Tinklas: {coin["network"]}

💵 Kiekis: {amount} {coin["symbol"]}
Perveskite TIKSLIAI tiek

Po pavedimo, prašome palaukti bent 10 minučių prieš susisiekiant su mumis.

Užsakymas bus automatiškai atšauktas po 20 minučių negavus pavedimo."""

            await query.edit_message_text(
                msg,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:

            print(
                "CoinMarketCap API error:",
                e
            )

            await query.edit_message_text(
                "❌ Nepavyko gauti dabartinės kriptovaliutos kainos.",
                parse_mode="Markdown"
            )

        return

    # --------------------------------------------------------
    # BACK
    # --------------------------------------------------------

    if query.data == "back":

        username = (
            f"@{query.from_user.username}"
            if query.from_user.username
            else "User"
        )

        message = f"""👋 Sveikas, {username}!

Šita vieta ne kiekvienam. Čia susirenka vyrai, kuriems patinka atviresnis turinys, drąsesnės temos ir dalykai, apie kuriuos viešai ne visada kalbama.

🎥 Lietuviškas turinys ir privati medžiaga, kurios viešai nepamatysi. 😉
💬 Jokių bereikalingų kalbų – atvira vyrų bendruomenė ir temos, kurios iš tikrųjų domina.
👀 Jei supranti, apie ką čia, turbūt ilgai aiškinti nereikia.

⸻

💳 {username}, pasirink mokėjimo planą (tai ne automatinė prenumerata) ir atsiskaitymo būdą, kad gautum pilną prieigą prie privataus turinio ir diskusijų."""

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 MĖNESIO NARYSTĖ: 14.99€ CRYPTO",
                    callback_data="mokejimas"
                )
            ]
        ]

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


# ============================================================
# HELP
# ============================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this message"
    )


# ============================================================
# APP
# ============================================================

app = Application.builder().token(TOKEN).build()


# Normal commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))


# Admin video/media commands
app.add_handler(CommandHandler("addvideo", add_video))
app.add_handler(CommandHandler("videos", list_videos))
app.add_handler(CommandHandler("deletevideo", delete_video))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("testvideo", test_video))


# Button handler
app.add_handler(
    CallbackQueryHandler(button_click)
)


# ============================================================
# HOURLY JOB
# ============================================================

app.job_queue.run_repeating(
    hourly_video,
    interval=2000,
    first=2000
)


# ============================================================
# START
# ============================================================

print("Bot is running...")
print(f"Database: {DB_PATH}")

app.run_polling()
