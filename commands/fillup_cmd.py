from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fill-up: Send gallons price [odometer].")

handler = CommandHandler("fillup", cmd_fillup)