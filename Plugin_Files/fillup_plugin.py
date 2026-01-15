# Plugin_Files/fillup_plugin.py
# Simple fill-up: gallons + price + optional odometer → confirm vehicle → save

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def initialize():
    print("[fillup_plugin] Initialized – /fillup ready")

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter fill-up:\n"
        "gallons price [odometer if full tank]\n\n"
        "Examples:\n"
        "12.5 45.67 65000    ← full tank\n"
        "10.2 38.90          ← partial\n\n"
        "Reply with your numbers."
    )

async def handle_fillup_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    args = text.split()

    if len(args) < 2:
        await update.message.reply_text("Need at least gallons and price.")
        return

    try:
        gallons = float(args[0])
        price = float(args[1])
    except ValueError:
        await update.message.reply_text("Gallons and price must be numbers.")
        return

    odometer = None
    is_full = False
    if len(args) > 2 and args[2].isdigit():
        odometer = int(args[2])
        is_full = True

    context.user_data["fillup_data"] = {
        "gallons": gallons,
        "price": price,
        "odometer": odometer,
        "is_full": is_full
    }

    user_id = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT vehicle_id, plate, year, make, model FROM vehicles WHERE user_id=?", (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        context.user_data.pop("fillup_data", None)
        return

    keyboard = []
    for v in vehicles:
        vid, plate, year, make, model = v
        button_text = f"{year} {make} {model} ({plate})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"fillup_confirm_{vid}")])

    keyboard.append([InlineKeyboardButton("Cancel", callback_data="fillup_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which vehicle?", reply_markup=reply_markup)

async def callback_fillup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "fillup_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop("fillup_data", None)
        return

    if not data.startswith("fillup_confirm_"):
        return

    vehicle_id = int(data.split("_")[-1])
    fillup_data = context.user_data.get("fillup_data")
    if not fillup_data:
        await query.edit_message_text("Session expired. Try /fillup again.")
        return

    gallons = fillup_data["gallons"]
    price = fillup_data["price"]
    odometer = fillup_data["odometer"]
    is_full = fillup_data["is_full"]

    fill_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, fill_date, is_full_tank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, update.effective_user.id, odometer, gallons, price, fill_date, 1 if is_full else 0))

        description = f"Fuel fill-up: {gallons} gal @ ${price:.2f}"
        c.execute('''
            INSERT INTO finance_records (type, amount, description, vehicle_id, timestamp)
            VALUES ('expense', ?, ?, ?, ?)
        ''', (price, description, vehicle_id, fill_date))

        conn.commit()

    context.user_data.pop("fillup_data", None)

    reply = f"Fill-up logged. {'Full tank' if is_full else 'Partial'}."
    await query.edit_message_text(reply)

def register(app: Application):
    app.add_handler(CommandHandler("fillup", cmd_fillup))
    app.add_handler(CallbackQueryHandler(callback_fillup_confirm, pattern="^fillup_confirm_|^fillup_cancel"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_fillup_input))
    print("[fillup_plugin] Registered")