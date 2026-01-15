# Plugin_Files/finance_plugin.py
# Version: 1.43.20260115 – Massive UX upgrade: /finance shows button menu

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[finance_plugin] Creating/updating finance_records table...")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,          -- expense, income, debt, asset
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

async def finance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main /finance command – shows button menu when no args
    """
    args = context.args

    # If args provided → old-style direct logging
    if args:
        return await finance_direct(update, context)

    # Otherwise → show beautiful button menu
    keyboard = [
        [
            InlineKeyboardButton("Expense 💸", callback_data="fin_expense"),
            InlineKeyboardButton("Income 💰", callback_data="fin_income"),
        ],
        [
            InlineKeyboardButton("Debt 📉", callback_data="fin_debt"),
            InlineKeyboardButton("Asset 📈", callback_data="fin_asset"),
        ],
        [
            InlineKeyboardButton("Balance ⚖️", callback_data="fin_balance"),
            InlineKeyboardButton("Net Worth 🌐", callback_data="fin_networth"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )

async def finance_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle old-style /finance <type> <amount> <desc> [category]"""
    args = context.args
    if len(args) < 2:
        await update.effective_message.reply_text("Missing amount or description.\nUse /finance for menu.")
        return

    sub = args[0].lower()
    try:
        amount = float(args[1])
    except ValueError:
        await update.effective_message.reply_text("Amount must be a number.")
        return

    desc = args[2] if len(args) > 2 else ""
    cat = args[3] if len(args) > 3 else None

    if sub in ('expense', 'income', 'debt', 'asset'):
        log_entry(sub, amount, desc, cat)
        await update.effective_message.reply_text(f"{sub.capitalize()} of ${amount:.2f} logged: {desc}")
    elif sub in ('balance', 'networth'):
        if sub == 'balance':
            bal = get_balance()
            await update.effective_message.reply_text(f"Current balance: ${bal:.2f}")
        else:
            nw = get_networth()
            await update.effective_message.reply_text(f"Net worth: ${nw:.2f}")
    else:
        await update.effective_message.reply_text("Unknown operation. Use the menu with /finance.")

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "fin_balance":
        bal = get_balance()
        await query.edit_message_text(f"Current balance: **${bal:.2f}**", parse_mode="Markdown")
        return

    if data == "fin_networth":
        nw = get_networth()
        await query.edit_message_text(f"Net worth: **${nw:.2f}**", parse_mode="Markdown")
        return

    # For logging types: expense/income/debt/asset
    # Reply asking for amount + desc
    type_map = {
        "fin_expense": "expense",
        "fin_income": "income",
        "fin_debt": "debt",
        "fin_asset": "asset"
    }
    entry_type = type_map.get(data)

    if entry_type:
        context.user_data["fin_pending"] = {"type": entry_type}
        await query.edit_message_text(
            f"Enter details for **{entry_type.capitalize()}**:\n"
            f"amount description [category]\n\n"
            f"Example: 45.67 Gas station Fuel\n"
            f"Reply with your entry."
        )
    else:
        await query.edit_message_text("Unknown action.")

async def handle_finance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reply messages for pending finance entries"""
    if "fin_pending" not in context.user_data:
        return  # Not waiting for finance input

    pending = context.user_data["fin_pending"]
    text = update.message.text.strip()
    args = text.split(maxsplit=2)

    if len(args) < 2:
        await update.message.reply_text("Need at least amount and description.")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    desc = args[1]
    cat = args[2] if len(args) > 2 else None

    log_entry(pending["type"], amount, desc, cat)
    await update.message.reply_text(
        f"{pending['type'].capitalize()} of **${amount:.2f}** logged: {desc}",
        parse_mode="Markdown"
    )

    # Clear pending state
    del context.user_data["fin_pending"]

def get_balance():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'income'")
        income = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'expense'")
        expense = c.fetchone()[0] or 0
        return income - expense

def get_networth():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type IN ('income', 'asset')")
        assets = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type IN ('expense', 'debt')")
        liabilities = c.fetchone()[0] or 0
        return assets - liabilities

def initialize():
    init_db()
    print("[finance_plugin] Initialized – /finance button menu ready")

# In telegram_plugin.py or wherever you register handlers, add:
# application.add_handler(CommandHandler("finance", finance_menu))
# application.add_handler(CallbackQueryHandler(finance_callback, pattern="^fin_"))
# application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_finance_input))