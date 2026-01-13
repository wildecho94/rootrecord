# Plugin_Files/vehicles_plugin.py
# Version: 20260113 – Vehicle management + MPG only (fill-up moved to fillup_plugin.py)

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
        c.execute("SELECT vehicle_id, plate, year, make, model FROM vehicles WHERE user_id=?", (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    keyboard = []
    for v in vehicles:
        vid, plate, year, make, model = v
        button_text = f"{year} {make} {model} ({plate})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"veh_menu_{vid}")])

    keyboard.append([InlineKeyboardButton("Add New Vehicle", callback_data="veh_add")])
    keyboard.append([InlineKeyboardButton("View MPG Stats", callback_data="veh_mpg")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Your vehicles:", reply_markup=reply_markup)

async def callback_vehicle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "veh_add":
        await query.edit_message_text("Use /vehicle add <Plate> <Year> <Make> <Model> <Odometer> to add a car.")
        return

    if data == "veh_mpg":
        await cmd_mpg(update, context)
        return

    if not data.startswith("veh_menu_"):
        return

    vehicle_id = int(data.split("_")[-1])
    context.user_data["selected_vehicle_id"] = vehicle_id

    keyboard = [
        [InlineKeyboardButton("View MPG", callback_data=f"veh_viewmpg_{vehicle_id}")],
        [InlineKeyboardButton("Back to list", callback_data="veh_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Vehicle actions:", reply_markup=reply_markup)

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT v.plate, v.year, v.make, v.model, AVG(f.mpg_calculated) as avg_mpg, MAX(f.mpg_calculated) as last_mpg
            FROM vehicles v
            LEFT JOIN fuel_records f ON v.vehicle_id = f.vehicle_id AND f.is_full_tank = 1
            WHERE v.user_id = ?
            GROUP BY v.vehicle_id
        ''', (user_id,))
        results = c.fetchall()

    if not results:
        await update.message.reply_text("No MPG data yet. Log full tank fill-ups first.")
        return

    text = "MPG Stats:\n"
    for row in results:
        plate, year, make, model, avg_mpg, last_mpg = row
        last_str = f"{last_mpg:.1f}" if last_mpg is not None else "N/A"
        avg_str = f"{avg_mpg:.1f}" if avg_mpg is not None else "N/A"
        text += f"{year} {make} {model} ({plate}): Last MPG {last_str}, Avg {avg_str}\n"

    await update.message.reply_text(text)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + MPG ready")