# Plugin_Files/vehicles_plugin.py
# Version: 20260113 – Multi-vehicle, button menu, MPG on full tank, /mpg command

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[vehicles_plugin] Creating vehicles & fuel_records tables...")
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                fill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                odometer INTEGER,                    -- required for full tanks
                gallons REAL NOT NULL,
                price REAL,
                station TEXT,
                notes TEXT,
                fill_date TEXT NOT NULL,
                is_full_tank INTEGER DEFAULT 0,      -- 1 = full tank (triggers MPG)
                mpg_calculated REAL,                 -- calculated MPG for this fill (if full)
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
            )
        ''')
        conn.commit()
    print("[vehicles_plugin] Vehicles & fuel tables ready")

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
        [InlineKeyboardButton("Log Fill-up", callback_data=f"veh_fill_{vehicle_id}")],
        [InlineKeyboardButton("View MPG", callback_data=f"veh_viewmpg_{vehicle_id}")],
        [InlineKeyboardButton("Back to list", callback_data="veh_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Vehicle actions:", reply_markup=reply_markup)

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "Enter fill-up details in this format:\n"
        "gallons price [station] [notes] [--full] [odometer (if full)]\n\n"
        "Example:\n"
        "12.5 45.67 Shell --full 65000\n"
        "or\n"
        "13.0 50.00 --full\n\n"
        "Reply with your input."
    )

async def handle_fillup_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = text.split()

    if len(args) < 2:
        await update.message.reply_text("Invalid format. Use: gallons price [station] [notes] [--full] [odometer (if full)]")
        return

    try:
        gallons = float(args[0])
        price = float(args[1])
    except ValueError:
        await update.message.reply_text("Gallons and price must be numbers.")
        return

    station = args[2] if len(args) > 2 else None
    notes = ' '.join(args[3:-1]) if len(args) > 3 else None
    is_full = "--full" in text.lower()

    odometer = None
    if is_full:
        if len(args) > 4 and args[-1].isdigit():
            odometer = int(args[-1])
        else:
            await update.message.reply_text("Full tank fill-up requires odometer as last number.")
            return

    # Store parsed data in context for confirmation
    context.user_data["fillup_data"] = {
        "gallons": gallons,
        "price": price,
        "station": station,
        "notes": notes,
        "is_full": is_full,
        "odometer": odometer
    }

    # Show confirmation buttons with user's vehicles
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT vehicle_id, plate, year, make, model FROM vehicles WHERE user_id=?", (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        del context.user_data["fillup_data"]
        return

    keyboard = []
    for v in vehicles:
        vid, plate, year, make, model = v
        button_text = f"{year} {make} {model} ({plate})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"fillup_confirm_{vid}")])

    keyboard.append([InlineKeyboardButton("Cancel", callback_data="fillup_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Confirm vehicle for this fill-up:", reply_markup=reply_markup)

async def callback_fillup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "fillup_cancel":
        await query.edit_message_text("Fill-up cancelled.")
        if "fillup_data" in context.user_data:
            del context.user_data["fillup_data"]
        return

    if not data.startswith("fillup_confirm_"):
        return

    vehicle_id = int(data.split("_")[-1])

    if "fillup_data" not in context.user_data:
        await query.edit_message_text("Session expired. Try /fillup again.")
        return

    data = context.user_data["fillup_data"]
    gallons = data["gallons"]
    price = data["price"]
    station = data["station"]
    notes = data["notes"]
    is_full = data["is_full"]
    odometer = data["odometer"]

    fill_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, station, notes, fill_date, is_full_tank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, update.effective_user.id, odometer, gallons, price, station, notes, fill_date, 1 if is_full else 0))

        description = f"Fuel fill-up: {gallons} gal @ ${price or 0:.2f}"
        c.execute('''
            INSERT INTO finance_records (type, amount, description, vehicle_id, timestamp)
            VALUES ('expense', ?, ?, ?, ?)
        ''', (price or 0, description, vehicle_id, fill_date))

        conn.commit()

    del context.user_data["fillup_data"]

    reply = f"Fill-up logged for vehicle {vehicle_id}. {'Full tank – MPG will be calculated.' if is_full else 'Partial fill-up logged.'}"
    await query.edit_message_text(reply)

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
        text += f"{year} {make} {model} ({plate}): Last MPG {last_mpg:.1f if last_mpg else 'N/A'}, Avg {avg_mpg:.1f if avg_mpg else 'N/A'}\n"

    await update.message.reply_text(text)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – multi-vehicle & fuel tracking ready")