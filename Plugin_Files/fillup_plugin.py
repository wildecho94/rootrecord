# Plugin_Files/fillup_plugin.py
# Version: 1.43.20260117 – Migrated to self-hosted MySQL (async, single DB, no locks, fixed syntax)

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from utils.db_mysql import get_db, init_mysql  # Shared self-hosted MySQL helper

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

    print("[fillup_plugin] Fuel table and index ready in MySQL")

async def cmd_fillup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter fill-up:\n"
        "gallons price [odometer if full tank]\n\n"
        "Examples:\n"
        "12.5 45.67 65000    ← full tank\n"
        "10.2 38.90          ← partial\n\n"
        "Reply with your numbers."
    )

async def handle_fillup_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    args = text.split()

    if len(args) < 2:
        await update.message.reply_text("Need at least gallons and price.")
        return

    try:
        gallons = float(args[0])
        price = float(args[1])
        odometer = float(args[2]) if len(args) > 2 else None
        is_full = odometer is not None
    except ValueError:
        await update.message.reply_text("Invalid numbers. Use decimals if needed.")
        return

    context.user_data['fillup_data'] = {
        'gallons': gallons,
        'price': price,
        'odometer': odometer,
        'is_full': is_full
    }

    keyboard = [
        [InlineKeyboardButton("Yes, full tank", callback_data="fillup_confirm_full"),
         InlineKeyboardButton("No, partial", callback_data="fillup_confirm_partial")],
        [InlineKeyboardButton("Cancel", callback_data="fillup_cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Fill-up: {gallons} gal @ ${price:.2f}\n"
        f"Odometer: {odometer if odometer else 'N/A'}\n\n"
        "Is this a full tank?",
        reply_markup=reply_markup
    )

async def callback_fillup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id
    print(f"[fillup callback DEBUG] User {user_id} tapped button: {data}")

    if data == "fillup_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop("fillup_data", None)
        return

    fillup_data = context.user_data.get("fillup_data")
    if not fillup_data:
        await query.edit_message_text("No fill-up data found. Use /fillup to start.")
        return

    gallons = fillup_data['gallons']
    price = fillup_data['price']
    odometer = fillup_data['odometer']
    is_full = data == "fillup_confirm_full" or fillup_data['is_full']
    fill_date = datetime.utcnow()

    # Replace with your vehicle ID logic (e.g. from context or user data)
    vehicle_id = 1  # Placeholder - replace with actual vehicle ID from user/vehicle plugin

    async for session in get_db():
        await session.execute(text('''
            INSERT INTO fuel_records (vehicle_id, user_id, odometer, gallons, price, fill_date, is_full_tank)
            VALUES (:vehicle_id, :user_id, :odometer, :gallons, :price, :fill_date, :is_full_tank)
        '''), {
            "vehicle_id": vehicle_id,
            "user_id": update.effective_user.id,
            "odometer": odometer,
            "gallons": gallons,
            "price": price,
            "fill_date": fill_date,
            "is_full_tank": 1 if is_full else 0
        })
        await session.commit()

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

    context.user_data.pop("fillup_data", None)

    reply = f"Fill-up logged. {'Full tank' if is_full else 'Partial'}."
    await query.edit_message_text(reply)

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[fillup_plugin] Initialized – /fillup ready")
