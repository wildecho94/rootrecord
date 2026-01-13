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
        # Get all vehicles for the user
        c.execute('''
            SELECT vehicle_id, plate, year, make, model, initial_odometer
            FROM vehicles
            WHERE user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    text = "MPG Stats:\n"
    has_data = False

    for veh in vehicles:
        vehicle_id, plate, year, make, model, initial_odometer = veh

        # Get all full-tank fills with odometer, ordered by date
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
        prev_odometer = initial_odometer  # Use initial as baseline for first fill

        for fill in full_tanks:
            current_odometer, gallons = fill[1], fill[2]
            if current_odometer is None or gallons <= 0:
                continue
            miles = current_odometer - prev_odometer
            if miles > 0:
                mpg = miles / gallons
                mpgs.append(mpg)
            prev_odometer = current_odometer  # Update for next interval

        if not mpgs:
            text += f"{year} {make} {model} ({plate}): No valid MPG intervals (check odometer progression)\n"
            continue

        has_data = True
        avg_mpg = sum(mpgs) / len(mpgs)
        last_mpg = mpgs[-1]
        text += f"{year} {make} {model} ({plate}): Last MPG {last_mpg:.1f}, Avg {avg_mpg:.1f} (over {len(mpgs)} intervals)\n"

    if not has_data:
        text += "\nNo MPG data yet. Log full tank fill-ups with odometer to start tracking."

    await update.message.reply_text(text)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + MPG ready")