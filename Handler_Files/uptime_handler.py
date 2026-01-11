# RootRecord Handler_Files/uptime_handler.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - command handler
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from Core_Files.uptime_core import get_stats, record_event, save_state, load_state
from datetime import datetime

last_start = datetime.utcnow()

async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_stats()
    text = (
        f"**Uptime Stats**\n"
        f"• Current: {s['current']}\n"
        f"• Total uptime: {s['total_uptime']}\n"
        f"• Total downtime: {s['total_downtime']}\n"
        f"• Uptime: {s['uptime_pct']}\n"
        f"• Last start: {s['last_start']}\n"
        f"• Last end: {s['last_end']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def register(app):
    app.add_handler(CommandHandler("uptime", uptime))
    print("[uptime] /uptime registered")