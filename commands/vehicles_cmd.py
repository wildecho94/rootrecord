from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Vehicles: (list coming soon).")

handler = CommandHandler("vehicles", cmd_vehicles)