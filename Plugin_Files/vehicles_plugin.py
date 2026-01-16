# Plugin_Files/vehicles_plugin.py
# Version: 20260118 – Full migration to async self-hosted MySQL, removed SQLite

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from utils.db_mysql import get_db, init_mysql

ROOT = Path(__file__).parent.parent

# ────────────────────────────────────────────────
# Database Setup
# ────────────────────────────────────────────────
async def init_db():
    print("[vehicles_plugin] Creating/updating vehicles & fuel_records tables in MySQL...")
    async for session in get_db():
        # Vehicles table
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                plate VARCHAR(20) NOT NULL,
                year INT NOT NULL,
                make VARCHAR(50) NOT NULL,
                model VARCHAR(100) NOT NULL,
                initial_odometer INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_user_plate (user_id, plate)
            )
        '''))
        # Fuel records (moved here from fillup_plugin if you want consolidation later)
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                odometer REAL,
                gallons REAL NOT NULL,
                price REAL NOT NULL,
                fill_date DATETIME NOT NULL,
                is_full_tank TINYINT DEFAULT 1,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_vehicle_fill_date (vehicle_id, fill_date)
            )
        '''))
        await session.commit()
    print("[vehicles_plugin] Vehicles & fuel tables ready in MySQL")

# ────────────────────────────────────────────────
# Helper: Get user's vehicles
# ────────────────────────────────────────────────
async def get_user_vehicles(user_id: int):
    vehicles = []
    async for session in get_db():
        result = await session.execute(text('''
            SELECT vehicle_id, plate, year, make, model, initial_odometer
            FROM vehicles
            WHERE user_id = :uid
            ORDER BY created_at DESC
        '''), {"uid": user_id})
        vehicles = result.fetchall()
    return vehicles

# ────────────────────────────────────────────────
# Add vehicle command
# ────────────────────────────────────────────────
async def cmd_vehicle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 6:
        await update.message.reply_text(
            "Usage: /vehicle add PLATE YEAR MAKE MODEL INITIAL_ODOMETER\n"
            "Example: /vehicle add ABC123 2020 Toyota Corolla 45000"
        )
        return

    plate = args[0].upper()
    try:
        year = int(args[1])
        make = args[2]
        model = " ".join(args[3:-1])  # Allow multi-word models
        odometer = int(args[-1])
    except ValueError:
        await update.message.reply_text("Year and odometer must be numbers.")
        return

    try:
        async for session in get_db():
            await session.execute(text('''
                INSERT INTO vehicles (user_id, plate, year, make, model, initial_odometer)
                VALUES (:uid, :plate, :year, :make, :model, :odo)
                ON DUPLICATE KEY UPDATE
                    year = VALUES(year),
                    make = VALUES(make),
                    model = VALUES(model),
                    initial_odometer = VALUES(initial_odometer)
            '''), {
                "uid": user_id,
                "plate": plate,
                "year": year,
                "make": make,
                "model": model,
                "odo": odometer
            })
            await session.commit()
        await update.message.reply_text(f"Vehicle **{plate}** ({year} {make} {model}) added/updated.")
    except Exception as e:
        await update.message.reply_text(f"Error adding vehicle: {str(e)}")

# ────────────────────────────────────────────────
# List vehicles command
# ────────────────────────────────────────────────
async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)

    if not vehicles:
        await update.message.reply_text("You have no vehicles yet. Add one with /vehicle add")
        return

    text = "**Your Vehicles**\n\n"
    for vid, plate, year, make, model, odo in vehicles:
        text += f"• **{plate}** – {year} {make} {model} (Initial: {odo} mi)\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# ────────────────────────────────────────────────
# MPG / Fuel Stats (consolidated here for now)
# ────────────────────────────────────────────────
async def calculate_fuel_stats(vehicle_id: int):
    fills = []
    async for session in get_db():
        result = await session.execute(text('''
            SELECT odometer, gallons, price, fill_date
            FROM fuel_records
            WHERE vehicle_id = :vid AND odometer IS NOT NULL
            ORDER BY fill_date ASC
        '''), {"vid": vehicle_id})
        fills = result.fetchall()

    if len(fills) < 2:
        return None

    total_miles = 0
    total_gallons = 0
    total_fuel_cost = 0

    for i in range(1, len(fills)):
        prev_odo = fills[i-1][0]
        curr_odo, gallons, price, _ = fills[i]
        miles = curr_odo - prev_odo
        if miles > 0 and gallons > 0:
            total_miles += miles
            total_gallons += gallons
            total_fuel_cost += price or 0

    if total_miles <= 0 or total_gallons <= 0:
        return None

    overall_mpg = total_miles / total_gallons
    fuel_cost_per_mile = total_fuel_cost / total_miles if total_miles > 0 else 0

    return {
        "mpg": overall_mpg,
        "miles": total_miles,
        "gallons": total_gallons,
        "cost": total_fuel_cost,
        "cost_per_mile": fuel_cost_per_mile,
        "fill_count": len(fills) - 1,  # intervals, not fills
        "period_start": fills[0][3].strftime("%Y-%m-%d"),
        "period_end": fills[-1][3].strftime("%Y-%m-%d")
    }

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    text = "**Fuel Efficiency Stats**\n\n"
    has_data = False

    for vid, plate, year, make, model, _ in vehicles:
        stats = await calculate_fuel_stats(vid)
        if stats:
            has_data = True
            text += f"**{year} {make} {model} ({plate})**\n"
            text += f"  • Overall MPG: **{stats['mpg']:.1f}**\n"
            text += f"  • Total miles: **{stats['miles']}** mi\n"
            text += f"  • Total fuel: **{stats['gallons']:.2f}** gal\n"
            text += f"  • Total fuel cost: **${stats['cost']:.2f}**\n"
            text += f"  • Cost per mile: **${stats['cost_per_mile']:.3f}**\n"
            text += f"  • Intervals counted: {stats['fill_count']}\n"
            text += f"  • Period: {stats['period_start']} to {stats['period_end']}\n\n"
        else:
            text += f"**{year} {make} {model} ({plate})**: Not enough fill-up data (need odometer + multiple fills)\n\n"

    if not has_data:
        text += "No usable fuel data yet. Log fill-ups with /fillup (include odometer)."

    await update.message.reply_text(text, parse_mode="Markdown")

# ────────────────────────────────────────────────
# Plugin initialization
# ────────────────────────────────────────────────
def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[vehicles_plugin] Initialized – MySQL vehicles + fuel stats ready")

# Note: Handlers should be added in your main plugin loader / telegram_plugin.py
# Example:
# app.add_handler(CommandHandler("vehicle", cmd_vehicle_add))  # or subcommands
# app.add_handler(CommandHandler("vehicles", cmd_vehicles))
# app.add_handler(CommandHandler("mpg", cmd_mpg))