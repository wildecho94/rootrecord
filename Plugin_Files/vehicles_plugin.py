# Plugin_Files/vehicles_plugin.py
# Version: 20260113 – Vehicle management + MPG only (fill-up moved to fillup_plugin.py)

import sqlite3
from pathlib import Path
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[vehicles_plugin] Creating vehicles table...")
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
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
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
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
    if len(args) != 5:
        await update.message.reply_text("Usage: /vehicle add <Plate> <Year> <Make> <Model> <Odometer>")
        return

    try:
        plate, year_str, make, model, odo_str = args
        year = int(year_str)
        odometer = int(odo_str)
    except ValueError:
        await update.message.reply_text("Year and odometer must be numbers.")
        return

    add_vehicle(user_id, plate, year, make, model, odometer)
    await update.message.reply_text(f"Vehicle {plate.upper()} added!")

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + MPG ready")