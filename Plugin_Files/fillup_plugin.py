# Plugin_Files/fillup_plugin.py
# Version: 20260113 – Isolated fill-up logging + finance integration

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def initialize():
    print("[fillup_plugin] Initialized – /fillup ready")
    # No DB init needed — uses existing tables from vehicles & finance plugins

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT vehicle_id, plate, year, make, model FROM vehicles WHERE user_id=?", (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    keyboard = []
    for v in vehicles:
        vid, plate, year, make, model = v
        button_text = f"{year} {make} {model} ({plate})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"fillup_select_{vid}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which vehicle did you fill up?", reply_markup=reply_markup)

async def callback_fillup_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("fillup_select_"):
        return

    vehicle_id = int(data.split("_")[-1])
    context.user_data["fillup_vehicle_id"] = vehicle_id

    await query.edit_message_text(
        f"Selected vehicle ID {vehicle_id}\n\n"
        "Enter fill-up details:\n"
        "gallons price [station] [notes] [--full]\n\n"
        "Example: 12.5 45.67 Shell --full\n"
        "Odometer required only for full tanks (add it as last number if needed)\n\n"
        "Reply to this message with your input."
    )

async def handle_fillup_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "fillup_vehicle_id" not in context.user_data:
        return

    user_id = update.effective_user.id
    vehicle_id = context.user_data["fillup_vehicle_id"]
    text = update.message.text.strip()
    args = text.split()

    if len(args) < 2:
        await update.message.reply_text("Format: gallons price [station] [notes] [--full]")
        return

    try:
        gallons = float(args[0])
        price = float(args[1])
    except ValueError:
        await update.message.reply_text("Gallons and price must be numbers.")
        return

    station = args[2] if len(args) > 2 else None
    notes = ' '.join(args[3:]) if len(args) > 3 else None
    is_full = "--full" in text.lower()

    odometer = None
    if is_full:
        if len(args) > 4 and args[-2].isdigit():
            odometer = int(args[-2])
        else:
            await update.message.reply_text("Full tank fill-up requires odometer. Reply with odometer value.")
            context.user_data["fillup_pending_full"] = True
            return

    fill_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, station, notes, fill_date, is_full_tank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, user_id, odometer, gallons, price, station, notes, fill_date, 1 if is_full else 0))

        # Auto-log as expense
        description = f"Fuel fill-up: {gallons} gal @ ${price or 0:.2f}"
        c.execute('''
            INSERT INTO finance_records (type, amount, description, vehicle_id, timestamp)
            VALUES ('expense', ?, ?, ?, ?)
        ''', (price or 0, description, vehicle_id, fill_date))

        conn.commit()

    del context.user_data["fillup_vehicle_id"]
    if "fillup_pending_full" in context.user_data:
        del context.user_data["fillup_pending_full"]

    reply = f"Fill-up logged for vehicle {vehicle_id}. {'Full tank – MPG will be calculated.' if is_full else 'Partial fill-up logged.'}"
    await update.message.reply_text(reply)

def register(app: Application):
    app.add_handler(CommandHandler("fillup", cmd_fillup))
    app.add_handler(CallbackQueryHandler(callback_fillup_select, pattern="^fillup_select_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_fillup_input))
    print("[fillup_plugin] /fillup + handlers registered")