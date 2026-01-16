# Plugin_Files/vehicles_plugin.py
# Version: 1.42.20260117 – Added debug logging for vehicle operations

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
            ORDER BY created_at
        '''), {"user_id": user_id})
        vehicles = result.fetchall()
    print(f"[vehicles] Found {len(vehicles)} vehicles for user {user_id}")
    return vehicles

async def cmd_vehicle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 5:
        await update.message.reply_text("Usage: /vehicle add PLATE YEAR MAKE MODEL ODOMETER")
        return

    plate, year, make, model = args[0], args[1], args[2], args[3]
    try:
        odometer = int(args[4])
        year = int(year)
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
                "make": make,
                "model": model,
                "odometer": odometer
            })
            await session.commit()
            await update.message.reply_text(f"Vehicle added: {year} {make} {model} ({plate})")
            print(f"[vehicles] Added vehicle for user {user_id}: {plate}")
        except Exception as e:
            await update.message.reply_text(f"Error adding vehicle: {str(e)}")
            print(f"[vehicles] Add failed for user {user_id}: {e}")

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)
    if not vehicles:
        await update.message.reply_text("No vehicles added yet. Use /vehicle add ...")
        return

    text = "**Your Vehicles**\n\n"
    for vid, plate, year, make, model, odo in vehicles:
        text += f"• {year} {make} {model} ({plate}) – Initial ODO: {odo} mi\n"
    await update.message.reply_text(text, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[vehicles_plugin] Initialized – vehicle commands ready")