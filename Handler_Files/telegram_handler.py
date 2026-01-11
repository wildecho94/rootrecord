# Handler_Files/telegram_handler.py
"""
Telegram plugin — advanced handlers & filters
All basic handlers are in telegram_core.py
"""

print("[telegram] handler loaded")

from telegram.ext import ContextTypes
from telegram import Update


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Example advanced handler: processes inline button clicks
    (Future plugins can add more handlers here)
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the click

    data = query.data
    await query.message.reply_text(f"You clicked button: {data}")

    # Optional: log callback
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Callback received: {data} from user {query.from_user.id}")