# commands/start_cmd.py
# Minimal: register on /start + welcome with article & commands

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from utils.db_mysql import get_db

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    async for session in get_db():
        await session.execute(
            text("""
                INSERT IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (:uid, :username, :first_name, :last_name)
            """),
            {
                "uid": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        )
        await session.commit()

    reply = f"""
Hello {user.first_name}! 👋 Welcome to **RootRecord**!

### What is RootRecord?
RootRecord is your personal tracking bot and dashboard for GPS pings, vehicle fuel logs, finance, uptime, and more. Self-hosted on MySQL, running 24/7 in Albuquerque, NM.

### Commands
/start — This message  
/uptime — Bot uptime stats  
/vehicles — Your vehicles & fuel stats  
/vehicle add PLATE YEAR MAKE MODEL ODO — Add vehicle  
/fillup — Log fuel fill-up  
/mpg — MPG & $/mile stats  
/finance — Finance menu  
/location — Log current location ping

More coming soon!
"""

    await update.message.reply_text(reply, parse_mode="Markdown")

handler = CommandHandler("start", start)