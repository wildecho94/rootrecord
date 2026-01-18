from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Uptime: Bot is running (full stats soon).")

handler = CommandHandler("uptime", cmd_uptime)