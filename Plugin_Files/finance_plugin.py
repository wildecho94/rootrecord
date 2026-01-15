# Plugin_Files/finance_plugin.py
# Version: 20260113 – Single shared table, auto-categories, added vehicle_id

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[finance_plugin] Creating/updating finance_records table...")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Base table
        c.execute('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,          -- expense, income, debt, asset
                amount REAL NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'Uncategorized',
                timestamp TEXT NOT NULL,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add vehicle_id column if missing (for fuel expenses)
        try:
            c.execute("ALTER TABLE finance_records ADD COLUMN vehicle_id INTEGER")
            print("[finance_plugin] Added vehicle_id column to finance_records")
        except sqlite3.OperationalError:
            pass  # column already exists
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
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/finance expense <amount> <desc> [category]\n"
            "/finance income <amount> <desc> [category]\n"
            "/finance debt <amount> <desc> [category]\n"
            "/finance asset <amount> <desc> [category]\n"
            "/finance balance\n"
            "/finance networth"
        )
        return

    sub = args[0].lower()
    if sub in ('balance', 'networth'):
        if sub == 'balance':
            bal = get_balance()
            await update.message.reply_text(f"Current balance: ${bal:.2f}")
        else:
            nw = get_networth()
            await update.message.reply_text(f"Net worth: ${nw:.2f}")
        return

    if len(args) < 3:
        await update.message.reply_text("Missing amount or description.")
        return

    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    desc = args[2]
    cat = args[3] if len(args) > 3 else None

    if sub in ('expense', 'income', 'debt', 'asset'):
        log_entry(sub, amount, desc, cat)
        await update.message.reply_text(f"{sub.capitalize()} of ${amount:.2f} logged: {desc}")
    else:
        await update.message.reply_text("Unknown operation. Use expense, income, debt, asset, balance, networth.")

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
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'income' OR type = 'asset'")
        assets = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'expense' OR type = 'debt'")
        liabilities = c.fetchone()[0] or 0
        return assets - liabilities

def initialize():
    init_db()
    print("[finance_plugin] Initialized – /finance ready")