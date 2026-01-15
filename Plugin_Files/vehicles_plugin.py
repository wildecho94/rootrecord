# Plugin_Files/vehicles_plugin.py
# Version: 20260115 – Cumulative MPG using ALL fills (full + partial), no ignoring

import sqlite3
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[vehicles_plugin] Creating vehicles table...")
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
        conn.commit()
    print("[vehicles_plugin] Vehicles table ready")

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
        await update.effective_message.reply_text("Usage: /vehicle add <Plate> <Year> <Make> <Model> <Odometer>")
        return

    plate = args[0].upper()
    try:
        year = int(args[1])
        odometer = int(args[-1])
    except ValueError:
        await update.effective_message.reply_text("Year and Odometer must be numbers.")
        return

    make = ' '.join(args[2:-1]) if len(args) > 5 else args[2]
    model = args[-2] if len(args) > 5 else args[3]

    add_vehicle(user_id, plate, year, make, model, odometer)
    await update.effective_message.reply_text(f"Vehicle added: {year} {make} {model} ({plate}), initial odometer {odometer}")

async def cmd_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT vehicle_id, plate, year, make, model
            FROM vehicles
            WHERE user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await update.effective_message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    keyboard = []
    for vid, plate, year, make, model in vehicles:
        keyboard.append([
            InlineKeyboardButton(f"{year} {make} {model} ({plate})", callback_data=f"veh_view_{vid}"),
            InlineKeyboardButton("MPG", callback_data=f"veh_mpg_{vid}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text("Your vehicles:", reply_markup=reply_markup)

async def show_vehicle_details(update: Update, context: ContextTypes.DEFAULT_TYPE, vehicle_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT plate, year, make, model, initial_odometer, created_at
            FROM vehicles
            WHERE vehicle_id = ? AND user_id = ?
        ''', (vehicle_id, update.effective_user.id))
        vehicle = c.fetchone()

    if not vehicle:
        await send_reply(update, "Vehicle not found or access denied.")
        return

    plate, year, make, model, initial_odometer, created_at = vehicle
    text = (
        f"**Vehicle Details**\n"
        f"• **Plate**: {plate}\n"
        f"• **Year / Make / Model**: {year} {make} {model}\n"
        f"• **Initial Odometer**: {initial_odometer} mi\n"
        f"• **Added**: {created_at.split('T')[0]}"
    )

    keyboard = [[InlineKeyboardButton("Back to list", callback_data="veh_list")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_vehicle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "veh_list":
        await cmd_vehicles(update, context)
        return

    if data.startswith("veh_view_"):
        vid = int(data.split("_")[-1])
        await show_vehicle_details(update, context, vid)

    elif data.startswith("veh_mpg_"):
        await cmd_mpg(update, context)

    elif data == "veh_cancel":
        await query.edit_message_text("Cancelled.")

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_from_button = bool(update.callback_query)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT vehicle_id, plate, year, make, model, initial_odometer
            FROM vehicles
            WHERE user_id = ?
        ''', (user_id,))
        vehicles = c.fetchall()

    if not vehicles:
        await send_reply(update, "No vehicles found. Add one with /vehicle add first.")
        return

    text = "**MPG Statistics (Cumulative – all fills included)**\n"
    if is_from_button:
        text += "_(from vehicle list)_\n"
    text += "───────────────\n\n"
    has_data = False

    for veh in vehicles:
        vid, plate, year, make, model, initial_odo = veh

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT odometer, gallons, fill_date
                FROM fuel_records
                WHERE vehicle_id = ? AND gallons > 0
                ORDER BY fill_date ASC
            ''', (vid,))
            fills = c.fetchall()

        if not fills:
            text += f"**{year} {make} {model} ({plate})**\n  No fill-up records yet\n\n"
            continue

        # Find the highest valid odometer (skip bogus low values)
        valid_odos = [f[0] for f in fills if f[0] is not None and f[0] >= 1000]
        if not valid_odos:
            text += f"**{year} {make} {model} ({plate})**\n  No valid odometer readings (all too low)\n\n"
            continue

        latest_odo = max(valid_odos)
        total_miles = latest_odo - initial_odo
        total_gallons = sum(f[1] for f in fills)

        if total_miles <= 0 or total_gallons <= 0:
            text += f"**{year} {make} {model} ({plate})**\n  Invalid totals (miles: {total_miles}, gallons: {total_gallons:.2f})\n\n"
            continue

        overall_mpg = total_miles / total_gallons

        text += f"**{year} {make} {model} ({plate})**\n"
        text += f"  • Overall MPG: **{overall_mpg:.1f}**\n"
        text += f"  • Total miles: {total_miles} mi\n"
        text += f"  • Total gallons added: {total_gallons:.2f} gal\n"
        text += f"  • Fills counted: {len(fills)}\n"
        text += f"  • Odo range: {initial_odo} → {latest_odo} mi\n"
        text += f"  • Period: {fills[0][2].split('T')[0]} to {fills[-1][2].split('T')[0]}\n\n"

        has_data = True

    if not has_data:
        text += "No usable data yet. Add fill-ups with realistic odometer values."

    await send_reply(update, text, parse_mode="Markdown")

async def send_reply(update: Update, text: str, reply_markup=None, parse_mode=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query:
        await update.callback_query.answer(text[:200], show_alert=len(text) > 200)

def initialize():
    init_db()
    print("[vehicles_plugin] Initialized – vehicle management + cumulative MPG ready")