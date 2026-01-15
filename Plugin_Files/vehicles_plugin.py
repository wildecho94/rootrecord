# Plugin_Files/vehicles_plugin.py
# Version: 20260115 – Improved MPG robustness, better reporting, gap warnings

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

    plate = args[0]
    try:
        year = int(args[1])
        odometer = int(args[4])
    except ValueError:
        await update.effective_message.reply_text("Year and Odometer must be numbers.")
        return

    make = ' '.join(args[2:-1])  # Allow multi-word makes/models
    model = args[-1] if len(args) > 5 else args[3]

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

    text = "**MPG Statistics**\n"
    if is_from_button:
        text += "_(from vehicle list)_\n"
    text += "───────────────\n\n"
    has_any_data = False

    for veh in vehicles:
        vid, plate, year, make, model, initial_odo = veh

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT fill_id, odometer, gallons, fill_date, is_full_tank
                FROM fuel_records
                WHERE vehicle_id = ?
                ORDER BY fill_date ASC
            ''', (vid,))
            all_fills = c.fetchall()

        full_fills = [f for f in all_fills if f[4] == 1 and f[1] is not None]

        if len(full_fills) < 2:
            text += f"**{year} {make} {model} ({plate})**\n"
            text += f"  Not enough full-tank data (need ≥2 full fills with odometer)\n\n"
            continue

        mpgs = []
        prev_odo = initial_odo
        used_count = 0

        for fill in full_fills:
            fill_id, odo, gal, date, _ = fill
            if odo <= prev_odo:
                print(f"[MPG WARN] {plate}: non-increasing odo {odo} <= {prev_odo} at {date}")
                continue
            miles = odo - prev_odo
            if gal > 0 and miles > 0:
                mpg = miles / gal
                mpgs.append(mpg)
                used_count += 1
            prev_odo = odo

        if not mpgs:
            text += f"**{year} {make} {model} ({plate})**\n"
            text += f"  No valid MPG intervals (check odometer progression)\n\n"
            continue

        has_any_data = True
        avg_mpg = sum(mpgs) / len(mpgs)
        last_mpg = mpgs[-1]

        text += f"**{year} {make} {model} ({plate})**\n"
        text += f"  • Last MPG: **{last_mpg:.1f}**\n"
        text += f"  • Average: **{avg_mpg:.1f}** ({len(mpgs)} intervals, {used_count} valid full fills)\n"
        text += f"  • From initial {initial_odo} to latest {prev_odo} mi\n\n"

    if not has_any_data:
        text += "No usable MPG data yet.\nLog full tank fill-ups with odometer readings to calculate efficiency."

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
    print("[vehicles_plugin] Initialized – vehicle management + improved MPG ready")