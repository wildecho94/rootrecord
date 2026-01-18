from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("MPG: (stats coming soon).")

handler = CommandHandler("mpg", cmd_mpg)