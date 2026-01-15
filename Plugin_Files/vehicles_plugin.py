# Plugin_Files/vehicles_plugin.py
# Version: 20260115 – Added vehicle details view + safe replies

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
        await update.effective_message.reply_text("Usage: /vehicle add <Plate> <Year> <Make> <Model> <Odometer>")
        return

    plate = args[0]
    try:
        year = int(args[1])
        odometer = int(args[4])
    except ValueError:
        await update.effective_message.reply_text("Year and Odometer must be numbers.")
        return

    make = args[2]
    model = args[3]

    add_vehicle(user_id, plate, year, make, model, odometer)
    await update.effective_message.reply_text(f"Vehicle added: {year} {make} {model} ({plate}), initial odometer {odometer}")

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

async def show_vehicle_details(update: Update, context: ContextTypes.DEFAULT_TYPE, vehicle_id: int):
    """Fetch and display details for a single vehicle"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT plate, year, make, model, initial_odometer, created_at
            FROM vehicles
            WHERE vehicle_id = ? AND user_id = ?
        ''', (vehicle_id, update.effective_user.id))
        vehicle = c.fetchone()

    if not vehicle:
        text = "Vehicle not found or you don't own it."
        await send_reply(update, text)
        return

    plate, year, make, model, initial_odometer, created_at = vehicle
    text = (
        f"**Vehicle Details**\n"
        f"• Plate: {plate}\n"
        f"• Year/Make/Model: {year} {make} {model}\n"
        f"• Initial Odometer: {initial_odometer} miles\n"
        f"• Added on: {created_at.split('T')[0]}"
    )

    keyboard = [[InlineKeyboardButton("Back to list", callback_data="veh_list")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_vehicle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "veh_list":
        # Re-show the full list
        await cmd_vehicles(update, context)
        await query.delete_message()  # Optional: clean up old message
        return

    if data.startswith("veh_view_"):
        vid = int(data.split("_")[-1])
        await show_vehicle_details(update, context, vid)

    elif data.startswith("veh_mpg_"):
        vid = int(data.split("_")[-1])
        # Optional: could filter MPG to this vehicle only in future
        # For now, show all (as before)
        await cmd_mpg(update, context)

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

async def send_reply(update: Update, text: str, reply_markup=None, parse_mode=None):
    """Safe reply helper for Message or CallbackQuery"""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query:
        await update.callback_query.answer(text, show_alert=True if len(text) > 200 else False)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + MPG + details ready")

# Handlers are registered in telegram_plugin.py