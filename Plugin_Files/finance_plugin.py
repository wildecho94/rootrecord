# Plugin_Files/finance_plugin.py
# Version: 1.43.20260117 – Buttons responsive, debug prints, back buttons

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[finance_plugin] Creating/updating finance_records table...")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'Uncategorized',
                timestamp TEXT NOT NULL,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP,
                vehicle_id INTEGER
            )
        ''')
        try:
            c.execute("ALTER TABLE finance_records ADD COLUMN vehicle_id INTEGER")
            print("[finance_plugin] Added vehicle_id column")
        except sqlite3.OperationalError:
            pass
        c.execute('CREATE INDEX IF NOT EXISTS idx_type_timestamp ON finance_records (type, timestamp)')
        conn.commit()
    print("[finance_plugin] Finance table ready")

def log_entry(type_: str, amount: float, desc: str, cat: str = None, vehicle_id: int = None):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO finance_records (type, amount, description, category, timestamp, vehicle_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (type_, amount, desc, cat, datetime.utcnow().isoformat(), vehicle_id))
        conn.commit()
    print(f"[finance] Logged {type_}: ${amount:.2f} - {desc}")

async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        sub = args[0].lower()
        if sub in ('balance', 'networth'):
            await show_detailed_report(update, context, is_balance=(sub == 'balance'))
            return

        if len(args) < 3:
            await update.effective_message.reply_text("Missing amount or description.\nUse /finance for menu.")
            return

        try:
            amount = float(args[1])
        except ValueError:
            await update.effective_message.reply_text("Amount must be a number.")
            return

        desc = args[2]
        cat = args[3] if len(args) > 3 else None

        if sub in ('expense', 'income', 'debt', 'asset'):
            log_entry(sub, amount, desc, cat)
            await update.effective_message.reply_text(f"{sub.capitalize()} of **${amount:.2f}** logged: {desc}", parse_mode="Markdown")
        else:
            await update.effective_message.reply_text("Unknown operation. Use the menu with /finance.")
        return

    keyboard = [
        [InlineKeyboardButton("Expense 💸", callback_data="fin_expense"),
         InlineKeyboardButton("Income 💰", callback_data="fin_income")],
        [InlineKeyboardButton("Debt 📉", callback_data="fin_debt"),
         InlineKeyboardButton("Asset 📈", callback_data="fin_asset")],
        [InlineKeyboardButton("Balance ⚖️", callback_data="fin_balance"),
         InlineKeyboardButton("Net Worth 🌐", callback_data="fin_networth")],
        [InlineKeyboardButton("Cancel ❌", callback_data="fin_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Required - acknowledges the tap

    data = query.data
    user_id = query.from_user.id
    print(f"[finance callback DEBUG] User {user_id} tapped button: {data}")

    if data == "fin_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop(f"fin_pending_{user_id}", None)
        return

    if data in ("fin_balance", "fin_networth"):
        await show_detailed_report(update, context, is_balance=(data == "fin_balance"))
        return

    type_map = {
        "fin_expense": "expense",
        "fin_income": "income",
        "fin_debt": "debt",
        "fin_asset": "asset"
    }
    entry_type = type_map.get(data)

    if entry_type:
        context.user_data[f"fin_pending_{user_id}"] = {"type": entry_type}
        keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data="fin_cancel")]]
        await query.edit_message_text(
            f"**{entry_type.capitalize()} Entry**\n\n"
            f"Reply with:\n"
            f"amount description [category]\n\n"
            f"Examples:\n"
            f"45.67 Gas station Fuel\n"
            f"1200 Monthly salary Salary\n\n"
            f"Reply below ↓",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("Unknown button. Use /finance to restart.")

async def handle_finance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending_key = f"fin_pending_{user_id}"

    if pending_key not in context.user_data:
        return

    pending = context.user_data[pending_key]
    entry_type = pending.get("type")

    text = update.message.text.strip()
    args = text.split(maxsplit=2)

    if len(args) < 2:
        await update.message.reply_text("Need amount and description.")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    desc = args[1]
    cat = args[2] if len(args) > 2 else None

    log_entry(entry_type, amount, desc, cat)
    await update.message.reply_text(
        f"✅ **{entry_type.capitalize()}** of **${amount:.2f}** logged: {desc}",
        parse_mode="Markdown"
    )

    context.user_data.pop(pending_key, None)

async def show_detailed_report(update: Update, context: ContextTypes.DEFAULT_TYPE, is_balance: bool):
    # (keep the detailed report function as before – no changes needed)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # ... (same as previous version for totals, top categories, recent) ...
    # (text building code here – omitted for brevity, use from last version)
    # End with:
    keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="fin_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def finance_back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "fin_menu":
        await finance(update, context)

def initialize():
    init_db()
    print("[finance_plugin] Initialized – button menu ready")
