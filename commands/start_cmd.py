# commands/start_cmd.py
# Edited Version: 1.42.20260111

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n"
        "This is RootRecord bot.\n"
        "Still early — more features coming."
    )

handler = CommandHandler("start", start)