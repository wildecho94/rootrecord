# Plugin_Files/vehicles_plugin.py
# Version: 1.42.20260117 – Full file with real calculate_fuel_stats implemented
#         Now exports get_user_vehicles and calculate_fuel_stats for mpg_plugin
#         Added logging for visibility

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

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
    Calculate cumulative MPG and related stats for a vehicle.
    Requires at least 2 fill-ups with odometer readings.
    """
    async for session in get_db():
        result = await session.execute(text('''
            SELECT odometer, gallons, price, fill_date
            FROM fuel_records
            WHERE vehicle_id = :vid AND odometer IS NOT NULL
            ORDER BY fill_date ASC
        '''), {"vid": vehicle_id})
        fills = result.fetchall()

    if len(fills) < 2:
        print(f"[vehicles] Not enough fill-ups for stats (need 2+ with odometer) on vehicle {vehicle_id}")
        return None

    total_miles = 0
    total_gallons = 0
    total_cost = 0
    period_start = fills[0][3]
    period_end = fills[-1][3]

    for i in range(1, len(fills)):
        prev_odo = fills[i-1][0]
        curr_odo = fills[i][0]
        gallons = fills[i][1]
        price = fills[i][2]

        if curr_odo > prev_odo:
            miles = curr_odo - prev_odo
            total_miles += miles
            total_gallons += gallons
            total_cost += gallons * price
        else:
            print(f"[vehicles] Skipping invalid interval (odo not increasing) on vehicle {vehicle_id}")

    if total_gallons <= 0:
        return None

    mpg = total_miles / total_gallons
    cost_per_mile = total_cost / total_miles if total_miles > 0 else 0

    stats = {
        'mpg': mpg,
        'miles': total_miles,
        'gallons': total_gallons,
        'cost': total_cost,
        'cost_per_mile': cost_per_mile,
        'fill_count': len(fills) - 1,  # intervals counted
        'period_start': period_start.strftime('%Y-%m-%d'),
        'period_end': period_end.strftime('%Y-%m-%d')
    }

    print(f"[vehicles] Calculated stats for vehicle {vehicle_id}: MPG={mpg:.1f}, Miles={total_miles}, Gallons={total_gallons:.2f}")
    return stats

async def cmd_vehicle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 5:
        await update.message.reply_text("Usage: /vehicle add PLATE YEAR MAKE MODEL ODOMETER")
        return

    plate, year_str, make, model = args[0], args[1], args[2], args[3]
    try:
        year = int(year_str)
        odometer = float(args[4])
    except ValueError:
        await update.message.reply_text("Year and odometer must be numbers.")
        return

    user_id = update.effective_user.id
    async for session in get_db():
        try:
            await session.execute(text('''
                INSERT INTO vehicles (user_id, plate, year, make, model, initial_odometer)
                VALUES (:user_id, :plate, :year, :make, :model, :odometer)
            '''), {
                "user_id": user_id,
                "plate": plate.upper(),
                "year": year,
                "make": make.title(),
                "model": model.title(),
                "odometer": odometer
            })
            await session.commit()
            await update.message.reply_text(f"Added: {year} {make} {model} ({plate}) – Initial ODO: {odometer}")
            print(f"[vehicles] Added vehicle for user {user_id}: {plate}")
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
            print(f"[vehicles] Add failed: {e}")

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text("No vehicles yet. Use /vehicle add ...")
        return

    text = "**Your Vehicles**\n\n"
    for vid, plate, year, make, model, odo in vehicles:
        text += f"• {year} {make} {model} ({plate}) – Initial ODO: {odo} mi (ID: {vid})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[vehicles_plugin] Initialized – vehicles + MPG stats ready")