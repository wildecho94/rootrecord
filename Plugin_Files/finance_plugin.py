# Plugin_Files/finance_plugin.py
# Version: 20260113 – Single shared table, auto-categories

"""
Finance plugin – /finance command + sub-operations
All data in ONE table: finance_records
Categories auto-created on first use
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def init_db():
    print("[finance_plugin] Creating finance_records table if missing...")
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
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_type_timestamp ON finance_records (type, timestamp)')
        conn.commit()
    print("[finance_plugin] Finance table ready")

def log_entry(type_: str, amount: float, description: str, category: str = None):
    timestamp = datetime.utcnow().isoformat()
    category = category or 'Uncategorized'
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO finance_records (type, amount, description, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (type_, amount, description, category, timestamp))
            conn.commit()
        print(f"[finance] Logged {type_} ${amount:.2f} ({category}): {description}")
    except sqlite3.Error as e:
        print(f"[finance] Log failed: {e}")

def get_balance():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        income = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='income'").fetchone()[0]
        expense = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='expense'").fetchone()[0]
        return income - expense

def get_networth():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        income = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='income'").fetchone()[0]
        expense = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='expense'").fetchone()[0]
        debt = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='debt'").fetchone()[0]
        assets = c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type='asset'").fetchone()[0]
        balance = income - expense
        return balance - debt + assets

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

def initialize():
    init_db()
    print("[finance_plugin] Initialized – /finance ready")