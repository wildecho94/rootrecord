# Plugin_Files/vehicles_plugin.py
# Version: 20260115 – Fixed callback → message reply crash in /mpg

import sqlite3
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[vehicles_plugin] Creating vehicles table...")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plate TEXT NOT NULL,
                year INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                initial_odometer INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, plate) ON CONFLICT IGNORE
            )
        ''')
        conn.commit()
    print("[vehicles_plugin] Vehicles table ready")

def add_vehicle(user_id: int, plate: str, year: int, make: str, model: str, odometer: int):
    plate = plate.upper()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO vehicles (user_id, plate, year, make, model, initial_odometer)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, plate, year, make, model, odometer))
        conn.commit()
    print(f"[vehicles] Added vehicle {plate} for user {user_id}")

async def cmd_vehicle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 5:
        await update.message.reply_text("Usage: /vehicle add <Plate> <Year> <Make> <Model> <Odometer>")
        return

    plate = args[0]
    try:
        year = int(args[1])
        odometer = int(args[4])
    except ValueError:
        await update.message.reply_text("Year and Odometer must be numbers.")
        return

    make = args[2]
    model = args[3]

    add_vehicle(user_id, plate, year, make, model, odometer)
    await update.message.reply_text(f"Vehicle added: {year} {make} {model} ({plate}), initial odometer {odometer}")

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT vehicle_id, plate, year, make, model
            FROM vehicles
            WHERE user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.effective_message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    keyboard = []
    for vid, plate, year, make, model in vehicles:
        keyboard.append([
            InlineKeyboardButton(f"{year} {make} {model} ({plate})", callback_data=f"veh_view_{vid}"),
            InlineKeyboardButton("MPG", callback_data=f"veh_mpg_{vid}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text("Your vehicles:", reply_markup=reply_markup)

async def callback_vehicle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("veh_view_"):
        vid = int(data.split("_")[-1])
        # TODO: show detailed view of vehicle
        await query.edit_message_text(f"Viewing details for vehicle ID {vid} (not implemented yet)")

    elif data.startswith("veh_mpg_"):
        vid = int(data.split("_")[-1])
        context.args = []  # reset args so cmd_mpg knows it's not a direct call
        await cmd_mpg(update, context)  # ← this line was calling cmd_mpg with callback update

    elif data == "veh_cancel":
        await query.edit_message_text("Cancelled.")

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT vehicle_id, plate, year, make, model, initial_odometer
            FROM vehicles
            WHERE user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        text = "No vehicles found. Add one with /vehicle add first."
        await send_reply(update, text)
        return

    text = "MPG Stats:\n"
    has_data = False

    for veh in vehicles:
        vehicle_id, plate, year, make, model, initial_odometer = veh

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT fill_id, odometer, gallons, fill_date
                FROM fuel_records
                WHERE vehicle_id = ? AND is_full_tank = 1 AND odometer IS NOT NULL
                ORDER BY fill_date ASC
            ''', (vehicle_id,))
            full_tanks = c.fetchall()

        if len(full_tanks) == 0:
            text += f"{year} {make} {model} ({plate}): No full-tank data yet\n"
            continue

        mpgs = []
        prev_odometer = initial_odometer

        for fill in full_tanks:
            current_odometer, gallons = fill[1], fill[2]
            if current_odometer is None or gallons <= 0:
                continue
            miles = current_odometer - prev_odometer
            if miles > 0:
                mpg = miles / gallons
                mpgs.append(mpg)
            prev_odometer = current_odometer

        if not mpgs:
            text += f"{year} {make} {model} ({plate}): No valid MPG intervals\n"
            continue

        has_data = True
        avg_mpg = sum(mpgs) / len(mpgs)
        last_mpg = mpgs[-1]
        text += f"{year} {make} {model} ({plate}): Last {last_mpg:.1f}, Avg {avg_mpg:.1f} ({len(mpgs)} intervals)\n"

    if not has_data:
        text += "\nNo MPG data yet. Log full tank fill-ups with odometer."

    await send_reply(update, text)

async def send_reply(update: Update, text: str):
    """Safe reply helper that works for both Message and CallbackQuery"""
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text)
    else:
        # Fallback: answer callback if possible
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + MPG ready")

# Register handlers (already in telegram_plugin.py or wherever you register)
# But for completeness:
# application.add_handler(CommandHandler("vehicles", cmd_vehicles))
# application.add_handler(CommandHandler("mpg", cmd_mpg))
# application.add_handler(CallbackQueryHandler(callback_vehicle_menu, pattern="^veh_"))