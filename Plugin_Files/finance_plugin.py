# Plugin_Files/finance_plugin.py
# Version: 1.43.20260116 – Buttons now guaranteed to respond + detailed reports

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

    # Show main menu
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

    sent = await update.effective_message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )
    # Optional: store message id if you ever want to edit it later
    context.user_data["fin_menu_msg_id"] = sent.message_id

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # This line is CRITICAL – tells Telegram the button was received

    data = query.data
    print(f"[finance debug] Button pressed: {data}")  # Console confirmation

    if data == "fin_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop("fin_pending", None)
        return

    if data in ("fin_balance", "fin_networth"):
        is_balance = data == "fin_balance"
        await show_detailed_report(update, context, is_balance)
        return

    # Prompt for input
    type_map = {
        "fin_expense": "expense",
        "fin_income": "income",
        "fin_debt": "debt",
        "fin_asset": "asset"
    }
    entry_type = type_map.get(data)

    if entry_type:
        context.user_data["fin_pending"] = {
            "type": entry_type,
            "original_message_id": query.message.message_id
        }
        await query.edit_message_text(
            f"**{entry_type.capitalize()} Entry**\n\n"
            f"Reply with:\n"
            f"amount description [category]\n\n"
            f"Examples:\n"
            f"• 45.67 Gas station Fuel\n"
            f"• 1200 Monthly salary Salary\n\n"
            f"Reply in this chat ↓",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("Unknown button. Use /finance to try again.")

async def handle_finance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "fin_pending" not in context.user_data:
        return

    pending = context.user_data["fin_pending"]
    entry_type = pending.get("type")

    text = update.message.text.strip()
    args = text.split(maxsplit=2)

    if len(args) < 2:
        await update.message.reply_text("Please provide at least amount and description.")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number (first value). Try again.")
        return

    desc = args[1]
    cat = args[2] if len(args) > 2 else None

    log_entry(entry_type, amount, desc, cat)
    await update.message.reply_text(
        f"✅ **{entry_type.capitalize()}** of **${amount:.2f}** logged: {desc}",
        parse_mode="Markdown"
    )

    # Clean up
    context.user_data.pop("fin_pending", None)

async def show_detailed_report(update: Update, context: ContextTypes.DEFAULT_TYPE, is_balance: bool):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'income'")
        total_income = c.fetchone()[0] or 0.0

        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'expense'")
        total_expense = c.fetchone()[0] or 0.0

        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'asset'")
        total_assets = c.fetchone()[0] or 0.0

        c.execute("SELECT SUM(amount) FROM finance_records WHERE type = 'debt'")
        total_debt = c.fetchone()[0] or 0.0

        balance = total_income - total_expense
        net_worth = (total_income + total_assets) - (total_expense + total_debt)

        # Top 5 expense categories
        c.execute('''
            SELECT category, SUM(amount) as total
            FROM finance_records
            WHERE type = 'expense' AND category IS NOT NULL AND category != 'Uncategorized'
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        ''')
        top_exp_cats = c.fetchall()

        # Recent 5 transactions
        c.execute('''
            SELECT type, amount, description, category, timestamp
            FROM finance_records
            ORDER BY id DESC
            LIMIT 5
        ''')
        recent = c.fetchall()

    title = "Balance Report" if is_balance else "Net Worth Report"
    main_value = balance if is_balance else net_worth
    main_label = "Current Balance" if is_balance else "Current Net Worth"

    text = f"**{title}**\n\n"
    text += f"**{main_label}**: **${main_value:,.2f}**\n\n"

    text += "**Summary**\n"
    text += f"• Total Income: **${total_income:,.2f}**\n"
    text += f"• Total Expenses: **${total_expense:,.2f}**\n"
    text += f"• Total Assets: **${total_assets:,.2f}**\n"
    text += f"• Total Debts: **${total_debt:,.2f}**\n\n"

    if top_exp_cats:
        text += "**Top Expense Categories**\n"
        for cat, amt in top_exp_cats:
            text += f"• {cat}: **${amt:,.2f}**\n"
        text += "\n"
    else:
        text += "**No categorized expenses yet.**\n\n"

    if recent:
        text += "**Recent Transactions**\n"
        for typ, amt, desc, cat, ts in recent:
            cat_str = f" ({cat})" if cat and cat != 'Uncategorized' else ""
            text += f"• {typ.capitalize()} ${amt:,.2f}{cat_str} – {desc[:40]}{'...' if len(desc)>40 else ''} ({ts.split('T')[0]})\n"
    else:
        text += "**No transactions logged yet.**\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, parse_mode="Markdown")

def initialize():
    init_db()
    print("[finance_plugin] Initialized – button menu + detailed reports ready")