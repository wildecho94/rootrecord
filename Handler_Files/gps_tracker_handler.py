# RootRecord Handler_Files/gps_tracker_handler.py
# Edited Version: 1.42.20260112

"""
GPS Tracker handler - processes shared and edited locations from Telegram
"""

from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from Core_Files.gps_tracker_core import process_location

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    process_location(update)
    await update.message.reply_text("Location received and stored! 📍")

def register_gps_handler(app):
    # Handle both new locations and edited locations with location
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.LOCATION & filters.UpdateType.EDITED_MESSAGE, handle_location))
    print("[gps_tracker] Registered location handler (new & edited)")