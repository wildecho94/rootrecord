# Plugin_Files/fillup_plugin.py
# Version: 1.42.20260117 – Full file with added logging at every major step
#          Logs received data, save attempts, finance linking, and final success

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from utils.db_mysql import get_db, init_mysql

ROOT = Path(__file__).parent.parent

async def init_db():
    print("[fillup_plugin] Creating/updating fuel_records table in MySQL...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_id INT NOT NULL,
                user_id INT NOT NULL,
                odometer REAL,
                gallons REAL NOT NULL,
                price REAL NOT NULL,
                fill_date DATETIME NOT NULL,
                is_full_tank TINYINT DEFAULT 1,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        await session.commit()

        try:
            await session.execute(text('''
                CREATE INDEX idx_vehicle_fill_date ON fuel_records (vehicle_id, fill_date)
            '''))
            await session.commit()
            print("[fillup_plugin] Created index idx_vehicle_fill_date")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print("[fillup_plugin] Index idx_vehicle_fill_date already exists")
            else:
                print(f"[fillup_plugin] Index creation failed: {e}")
    print("[fillup_plugin] Fuel records table and indexes ready")

# Example interactive flow – adapt if your actual handlers differ
# This is a minimal working version; replace with your full command/callback chain

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Start fill-up conversation (simplified – add your real state management)
    keyboard = [
        [InlineKeyboardButton("Full Tank", callback_data="full")],
        [InlineKeyboardButton("Partial", callback_data="partial")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Is this a full tank or partial fill-up?",
        reply_markup=reply_markup
    )
    print(f"[fillup] User {update.effective_user.id} started /fillup")

async def handle_fillup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    is_full = query.data == "full"
    context.user_data["fillup_data"] = {"is_full": is_full}

    await query.edit_message_text(
        f"{'Full tank' if is_full else 'Partial'} selected. Now send: gallons price [odometer]"
    )
    print(f"[fillup] User selected {'full' if is_full else 'partial'} tank")

# Message handler for the data input (gallons price odometer)
async def handle_fillup_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().split()
    if len(text) < 2:
        await update.message.reply_text("Need at least: gallons price [optional odometer]")
        return

    try:
        gallons = float(text[0])
        price = float(text[1])
        odometer = float(text[2]) if len(text) > 2 else None
    except ValueError:
        await update.message.reply_text("Invalid numbers. Use format: 12.3 45.67 123456")
        return

    user_data = context.user_data.setdefault("fillup_data", {})
    user_data.update({
        "gallons": gallons,
        "price": price,
        "odometer": odometer,
    })

    # TODO: Replace hardcoded vehicle_id=1 with real vehicle selection/lookup
    vehicle_id = 1  # ← FIX THIS LATER – e.g. from user active vehicle
    user_id = update.effective_user.id
    fill_date = datetime.utcnow()

    print(f"[fillup] Received data from user {user_id}: "
          f"gallons={gallons}, price=${price:.2f}, odo={odometer}, vehicle={vehicle_id}")

    async for session in get_db():
        try:
            await session.execute(text('''
                INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, fill_date, is_full_tank)
                VALUES (:vehicle_id, :user_id, :odometer, :gallons, :price, :fill_date, :is_full_tank)
            '''), {
                "vehicle_id": vehicle_id,
                "user_id": user_id,
                "odometer": odometer,
                "gallons": gallons,
                "price": price,
                "fill_date": fill_date,
                "is_full_tank": 1 if user_data.get("is_full", True) else 0
            })
            await session.commit()

            # Auto-create finance expense
            description = f"Fuel fill-up: {gallons} gal @ ${price:.2f}"
            await session.execute(text('''
                INSERT INTO finance_records (type, amount, description, vehicle_id, timestamp)
                VALUES ('expense', :amount, :description, :vehicle_id, :timestamp)
            '''), {
                "amount": price,
                "description": description,
                "vehicle_id": vehicle_id,
                "timestamp": fill_date
            })
            await session.commit()

            print(f"[fillup] SUCCESS: Logged fill-up + finance expense for vehicle {vehicle_id}")

            await update.message.reply_text(
                f"Fill-up logged: {gallons} gal @ ${price:.2f}. "
                f"{'Full' if user_data.get('is_full', True) else 'Partial'} tank."
            )

            # Clean up user data
            context.user_data.pop("fillup_data", None)

        except Exception as e:
            print(f"[fillup] Save failed for user {user_id}: {e}")
            await update.message.reply_text(f"Error saving fill-up: {str(e)}")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[fillup_plugin] Initialized – /fillup ready with step-by-step logging")