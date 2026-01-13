# Plugin_Files/pg_plugin.pym
# Version: 20260113 – Dedicated MPG stats & calculations

"""
MPG plugin – /mpg command to view per-vehicle fuel efficiency
Calculates MPG only on full-tank fill-ups with odometer
Running average per vehicle
"""

import sqlite3
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def calculate_mpg_for_vehicle(vehicle_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT fill_id, odometer, gallons, fill_date
            FROM fuel_records
            WHERE vehicle_id = ? AND is_full_tank = 1 AND odometer IS NOT NULL
            ORDER BY fill_date ASC
        ''', (vehicle_id,))
        full_tanks = c.fetchall()

    if len(full_tanks) < 2:
        return None, None  # not enough full tanks for MPG

    mpgs = []
    for i in range(1, len(full_tanks)):
        prev = full_tanks[i-1]
        curr = full_tanks[i]
        miles = curr[1] - prev[1]
        gallons_used = curr[2]  # current fill gallons (assumes previous partials included)
        if gallons_used > 0:
            mpg = miles / gallons_used
            mpgs.append(mpg)

    if not mpgs:
        return None, None

    avg_mpg = sum(mpgs) / len(mpgs)
    last_mpg = mpgs[-1]
    return last_mpg, avg_mpg

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT v.vehicle_id, v.plate, v.year, v.make, v.model
            FROM vehicles v
            WHERE v.user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    text = "MPG Stats:\n"
    has_data = False
    for v in vehicles:
        vid, plate, year, make, model = v
        last_mpg, avg_mpg = calculate_mpg_for_vehicle(vid)
        if last_mpg is not None:
            has_data = True
            text += f"{year} {make} {model} ({plate}): Last MPG {last_mpg:.1f}, Avg {avg_mpg:.1f}\n"
        else:
            text += f"{year} {make} {model} ({plate}): No full-tank data yet\n"

    if not has_data:
        text += "\nNo MPG data yet. Log full tank fill-ups (with odometer and --full) to start tracking."

    await update.message.reply_text(text)

def initialize():
    print("[mpg_plugin] Initialized – /mpg stats ready")