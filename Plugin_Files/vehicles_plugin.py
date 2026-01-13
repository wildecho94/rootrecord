# Plugin_Files/vehicles_plugin.py
# Version: 20260113 – Multi-vehicle + fuel fill-ups tied to finance + MPG

"""
Vehicles plugin – manage multiple vehicles, log fuel fill-ups, calculate MPG
All vehicle/fuel data in ONE table: fuel_records
Fuel-ups auto-log as expense in finance_records
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
                name TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name) ON CONFLICT IGNORE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                fill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                odometer INTEGER NOT NULL,
                gallons REAL NOT NULL,
                price REAL,
                station TEXT,
                notes TEXT,
                fill_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
            )
        ''')
        conn.commit()
    print("[vehicles_plugin] Vehicles & fuel tables ready")

def add_vehicle(user_id: int, name: str, make: str = None, model: str = None, year: int = None):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO vehicles (user_id, name, make, model, year)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, make, model, year))
        conn.commit()
    print(f"[vehicles] Added vehicle '{name}' for user {user_id}")

async def cmd_addvehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addvehicle \"My Car\" [make model year]")
        return

    name = args[0]
    make = model = year = None
    if len(args) >= 4:
        make, model, year = args[1], args[2], args[3]
    add_vehicle(user_id, name, make, model, year)
    await update.message.reply_text(f"Vehicle '{name}' added.")

def log_fillup(user_id: int, vehicle_name: str, odometer: int, gallons: float, price: float = None, station: str = None, notes: str = None):
    fill_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT vehicle_id FROM vehicles WHERE user_id=? AND name=?", (user_id, vehicle_name))
        row = c.fetchone()
        if not row:
            print(f"[vehicles] Vehicle '{vehicle_name}' not found")
            return False
        vehicle_id = row[0]

        c.execute('''
            INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, station, notes, fill_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, user_id, odometer, gallons, price, station, notes, fill_date))

        # Auto-log as expense in finance_records
        description = f"Fuel fill-up: {gallons} gal @ ${price or 0:.2f} ({vehicle_name})"
        c.execute('''
            INSERT INTO finance_records (type, amount, description, vehicle_id, timestamp)
            VALUES ('expense', ?, ?, ?, ?)
        ''', (price or 0, description, vehicle_id, fill_date))

        conn.commit()
    print(f"[vehicles] Fill-up logged for '{vehicle_name}'")
    return True

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 4:
        await update.message.reply_text("Usage: /fillup \"Vehicle Name\" odometer gallons price [station] [notes]")
        return

    vehicle_name = args[0]
    try:
        odometer = int(args[1])
        gallons = float(args[2])
        price = float(args[3])
    except ValueError:
        await update.message.reply_text("Odometer, gallons, price must be numbers.")
        return

    station = args[4] if len(args) > 4 else None
    notes = ' '.join(args[5:]) if len(args) > 5 else None

    success = log_fillup(user_id, vehicle_name, odometer, gallons, price, station, notes)
    if success:
        await update.message.reply_text(f"Fill-up logged for '{vehicle_name}'. MPG pending next fill.")
    else:
        await update.message.reply_text(f"Vehicle '{vehicle_name}' not found. Use /addvehicle first.")

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – multi-vehicle & fuel tracking ready")