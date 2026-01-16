# Plugin_Files/vehicles_plugin.py
# Version: 1.42.20260117 – Full file with REAL calculate_fuel_stats implemented
#         All calculations use miles and gallons (US units) as requested
#         Exports get_user_vehicles and calculate_fuel_stats for mpg_plugin
#         Added logging + basic error handling
#         /vehicle add and /vehicles commands included for completeness

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

from utils.db_mysql import get_db, init_mysql

ROOT = Path(__file__).parent.parent

async def init_db():
    print("[vehicles_plugin] Creating/updating vehicles table in MySQL...")
    async for session in get_db():
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
        await session.commit()
    print("[vehicles_plugin] Vehicles table ready")

async def get_user_vehicles(user_id: int):
    """Fetch all vehicles for a user, ordered by creation date."""
    vehicles = []
    async for session in get_db():
        result = await session.execute(text('''
            SELECT vehicle_id, plate, year, make, model, initial_odometer
            FROM vehicles
            WHERE user_id = :user_id
            ORDER BY created_at ASC
        '''), {"user_id": user_id})
        vehicles = result.fetchall()
    print(f"[vehicles] Loaded {len(vehicles)} vehicles for user {user_id}")
    return vehicles

async def calculate_fuel_stats(vehicle_id: int):
    """
    Calculate real cumulative MPG and related stats for a vehicle.
    - Uses miles and gallons (US units) exclusively
    - Requires at least 2 fill-ups with valid increasing odometer readings
    - Returns dict with mpg, miles, gallons, cost, cost_per_mile, fill_count, period
    - Skips invalid intervals (odo not increasing)
    """
    async for session in get_db():
        result = await session.execute(text('''
            SELECT odometer, gallons, price, fill_date
            FROM fuel_records
            WHERE vehicle_id = :vid 
              AND odometer IS NOT NULL
            ORDER BY fill_date ASC, id ASC
        '''), {"vid": vehicle_id})
        fills = result.fetchall()

    if len(fills) < 2:
        print(f"[vehicles] Not enough fill-ups for MPG stats (need 2+ with odometer) on vehicle {vehicle_id}")
        return None

    total_miles = 0.0
    total_gallons = 0.0
    total_cost = 0.0
    period_start = fills[0][3]
    period_end = fills[-1][3]
    valid_intervals = 0

    for i in range(1, len(fills)):
        prev_odo = fills[i-1][0]
        curr_odo = fills[i][0]
        gallons = fills[i][1]
        price = fills[i][2]

        if curr_odo > prev_odo and gallons > 0:
            miles = curr_odo - prev_odo
            total_miles += miles
            total_gallons += gallons
            total_cost += gallons * price
            valid_intervals += 1
            print(f"[vehicles] Valid interval on vehicle {vehicle_id}: {miles:.1f} mi / {gallons:.3f} gal")
        else:
            print(f"[vehicles] Skipped invalid interval on vehicle {vehicle_id}: odo {prev_odo} → {curr_odo}, gallons {gallons}")

    if total_gallons <= 0 or valid_intervals == 0:
        print(f"[vehicles] No valid MPG data after filtering for vehicle {vehicle_id}")
        return None

    mpg = total_miles / total_gallons
    cost_per_mile = total_cost / total_miles if total_miles > 0 else 0.0

    stats = {
        'mpg': mpg,
        'miles': total_miles,
        'gallons': total_gallons,
        'cost': total_cost,
        'cost_per_mile': cost_per_mile,
        'fill_count': valid_intervals,
        'period_start': period_start.strftime('%Y-%m-%d'),
        'period_end': period_end.strftime('%Y-%m-%d')
    }

    print(f"[vehicles] MPG stats calculated for vehicle {vehicle_id}: "
          f"{mpg:.1f} mpg over {total_miles:.0f} miles / {total_gallons:.2f} gallons")
    return stats

async def cmd_vehicle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 5:
        await update.message.reply_text(
            "Usage: /vehicle add PLATE YEAR MAKE MODEL INITIAL_ODO\n"
            "Example: /vehicle add ABC123 2014 Chevy Cruze 123456"
        )
        return

    plate = args[0].upper()
    try:
        year = int(args[1])
        make = args[2]
        model = ' '.join(args[3:-1])  # allow multi-word models
        initial_odo = float(args[-1])
    except ValueError:
        await update.message.reply_text("Year must be integer, odometer must be number.")
        return

    user_id = update.effective_user.id
    async for session in get_db():
        try:
            await session.execute(text('''
                INSERT INTO vehicles (user_id, plate, year, make, model, initial_odometer)
                VALUES (:user_id, :plate, :year, :make, :model, :odometer)
            '''), {
                "user_id": user_id,
                "plate": plate,
                "year": year,
                "make": make,
                "model": model,
                "odometer": initial_odo
            })
            await session.commit()
            await update.message.reply_text(
                f"Vehicle added successfully:\n"
                f"{year} {make} {model} ({plate})\n"
                f"Initial odometer: {initial_odo} miles"
            )
            print(f"[vehicles] Added vehicle for user {user_id}: {plate} ({year} {make} {model})")
        except Exception as e:
            await update.message.reply_text(f"Error adding vehicle: {str(e)}")
            print(f"[vehicles] Add failed for user {user_id}: {e}")

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text(
            "You have no vehicles yet.\n"
            "Add one: /vehicle add PLATE YEAR MAKE MODEL ODOMETER"
        )
        return

    text = "**Your Vehicles**\n\n"
    for vid, plate, year, make, model, odo in vehicles:
        text += f"• {year} {make} {model} ({plate})\n"
        text += f"  Initial odometer: {odo} miles (ID: {vid})\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")
    print(f"[vehicles] Listed {len(vehicles)} vehicles for user {user_id}")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[vehicles_plugin] Initialized – vehicles + real MPG calculation ready")