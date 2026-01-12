# RootRecord Handler_Files/gps_tracker_handler.py
# Edited Version: 1.42.20260111

"""
GPS Tracker handler - processes shared locations from Telegram
"""

from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from Core_Files.gps_tracker_core import process_location

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    process_location(update)
    await update.message.reply_text("Location received and stored! 📍")

def register_gps_handler(app):
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    print("[gps_tracker] Registered location handler")