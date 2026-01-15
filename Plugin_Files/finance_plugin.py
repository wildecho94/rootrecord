# Plugin_Files/finance_plugin.py
# Version: 1.43.20260116 – Fixed "nothing happened" on button tap + better flow

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

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

async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        # Old direct style still supported
        sub = args[0].lower()
        if sub in ('balance', 'networth'):
            if sub == 'balance':
                bal = get_balance()
                await update.effective_message.reply_text(f"Current balance: **${bal:.2f}**", parse_mode="Markdown")
            else:
                nw = get_networth()
                await update.effective_message.reply_text(f"Net worth: **${nw:.2f}**", parse_mode="Markdown")
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

    # No args → show menu
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
        [
            InlineKeyboardButton("Cancel ❌", callback_data="fin_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "fin_cancel":
        await query.edit_message_text("Cancelled.")
        return

    if data == "fin_balance":
        bal = get_balance()
        await query.edit_message_text(f"Current balance: **${bal:.2f}**", parse_mode="Markdown")
        return

    if data == "fin_networth":
        nw = get_networth()
        await query.edit_message_text(f"Net worth: **${nw:.2f}**", parse_mode="Markdown")
        return

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
            f"Reply with: amount description [category]\n\n"
            f"Examples:\n"
            f"45.67 Gas station Fuel\n"
            f"1200.00 Monthly salary Salary\n"
            f"Reply below ↓"
        )
    else:
        await query.edit_message_text("Unknown action. Try /finance again.")

async def handle_finance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "fin_pending" not in context.user_data:
        return

    pending = context.user_data.get("fin_pending", {})
    entry_type = pending.get("type")

    if not entry_type:
        await update.message.reply_text("Session expired. Use /finance to start again.")
        context.user_data.pop("fin_pending", None)
        return

    text = update.message.text.strip()
    args = text.split(maxsplit=2)

    if len(args) < 2:
        await update.message.reply_text("Need at least amount and description.\nTry again or /finance to restart.")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("First number must be the amount.\nExample: 45.67 Gas Fuel")
        return

    desc = args[1]
    cat = args[2] if len(args) > 2 else None

    log_entry(entry_type, amount, desc, cat)
    await update.message.reply_text(
        f"✅ {entry_type.capitalize()} of **${amount:.2f}** logged: {desc}",
        parse_mode="Markdown"
    )

    context.user_data.pop("fin_pending", None)

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
    print("[finance_plugin] Initialized – button menu ready")

# Registration (add this in telegram_plugin.py where other handlers are added):
# application.add_handler(CommandHandler("finance", finance))
# application.add_handler(CallbackQueryHandler(finance_callback, pattern="^fin_"))
# application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_finance_input))