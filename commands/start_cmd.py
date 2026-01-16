# commands/start_cmd.py
# Final, clean version – auto-creates users table on first /start + registers user + welcome with article & command list
# No datetime, no extra prints, no crash risk, only what you asked for

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from utils.db_mysql import get_db

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    async for session in get_db():
        # Auto-create users table if missing (one-time, safe)
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        await session.commit()

        # Register user (INSERT IGNORE = safe, no duplicate crash)
        await session.execute(
            text("""
                INSERT IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (:uid, :username, :first_name, :last_name)
            """),
            {
                "uid": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            }
        )
        await session.commit()

    # Send welcome (always full version for simplicity)
    reply = f"""
Hello {first_name}! 👋 Welcome to **RootRecord**!

You've been registered.

### What is RootRecord?
RootRecord is your personal tracking bot and dashboard.  
It's built for logging real-time GPS pings (with reverse geocoding), vehicle fuel fill-ups (MPG & $/mile stats), finance transactions, system uptime, and more.  
Currently running on a Dell OptiPlex 7060 in Albuquerque, NM — 24/7, with Telegram bot + Flask web dashboard via Cloudflare Tunnel.

It's modular (plugins), self-hosted (MySQL backend), and still in active development — more features coming soon.

### Available Commands
/start — Show this welcome message (re-registers if needed)  
/uptime — Lifetime bot uptime stats (up/down time, percentage)  
/vehicles — List your vehicles + fuel stats  
/vehicle add PLATE YEAR MAKE MODEL ODOMETER — Add a new vehicle  
/fillup — Log a fuel fill-up (gallons, price, odometer, full/partial)  
/mpg — View cumulative MPG & fuel cost per mile per vehicle  
/finance — Open finance menu (add income/expense, view reports)  
/location — Send your live location to log a ping (auto-geocoded)

More coming: activities, weather on pings, crypto tracking, etc.

Enjoy — send locations, fuel logs, or anything anytime!
"""

    await update.message.reply_text(reply, parse_mode="Markdown")

handler = CommandHandler("start", start)