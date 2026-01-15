# Plugin_Files/finance_plugin.py
# Version: 1.43.20260117 – Buttons guaranteed to respond, debug prints, back buttons

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

    # Main menu
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
    await query.answer()  # This MUST be called first – Telegram requirement

    data = query.data
    user_id = query.from_user.id
    print(f"[finance callback] User {user_id} pressed: {data}")

    if data == "fin_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop(f"fin_pending_{user_id}", None)
        return

    if data in ("fin_balance", "fin_networth"):
        is_balance = data == "fin_balance"
        await show_detailed_report(update, context, is_balance)
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
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"**{entry_type.capitalize()} Entry**\n\n"
            f"Reply in this chat with:\n"
            f"`amount description [category]`\n\n"
            f"Examples:\n"
            f"• 45.67 Gas station Fuel\n"
            f"• 1200 Monthly salary Salary\n\n"
            f"Waiting for your reply ↓",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("Unknown button action. Try /finance again.")

async def handle_finance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending_key = f"fin_pending_{user_id}"

    if pending_key not in context.user_data:
        return  # Not waiting for this user

    pending = context.user_data[pending_key]
    entry_type = pending.get("type")

    text = update.message.text.strip()
    args = text.split(maxsplit=2)

    if len(args) < 2:
        await update.message.reply_text("Need amount and description at minimum.\nReply again or /finance to restart.")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("First value must be the amount (e.g. 45.67).")
        return

    desc = args[1]
    cat = args[2] if len(args) > 2 else None

    log_entry(entry_type, amount, desc, cat)
    await update.message.reply_text(
        f"✅ **{entry_type.capitalize()}** of **${amount:.2f}** logged: {desc}\n\nUse /finance for more.",
        parse_mode="Markdown"
    )

    context.user_data.pop(pending_key, None)

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

        c.execute('''
            SELECT category, SUM(amount) as total
            FROM finance_records
            WHERE type = 'expense' AND category IS NOT NULL AND category != 'Uncategorized'
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        ''')
        top_exp = c.fetchall()

        c.execute('''
            SELECT type, amount, description, category, timestamp
            FROM finance_records
            ORDER BY id DESC
            LIMIT 5
        ''')
        recent = c.fetchall()

    title = "Balance Report" if is_balance else "Net Worth Report"
    main_val = balance if is_balance else net_worth
    main_lbl = "Current Balance" if is_balance else "Current Net Worth"

    text = f"**{title}**\n\n"
    text += f"**{main_lbl}**: **${main_val:,.2f}**\n\n"

    text += "**Overview**\n"
    text += f"• Income: **${total_income:,.2f}**\n"
    text += f"• Expenses: **${total_expense:,.2f}**\n"
    text += f"• Assets: **${total_assets:,.2f}**\n"
    text += f"• Debts: **${total_debt:,.2f}**\n\n"

    if top_exp:
        text += "**Top Expenses by Category**\n"
        for cat, amt in top_exp:
            text += f"• {cat}: **${amt:,.2f}**\n"
        text += "\n"
    else:
        text += "**No categorized expenses yet.**\n\n"

    if recent:
        text += "**Recent Activity (last 5)**\n"
        for typ, amt, desc, cat, ts in recent:
            cat_str = f" ({cat})" if cat and cat != 'Uncategorized' else ""
            text += f"• {typ.capitalize()} ${amt:,.2f}{cat_str} – {desc[:50]}{'...' if len(desc)>50 else ''} ({ts.split('T')[0]})\n"
    else:
        text += "**No transactions yet.**\n"

    keyboard = [[InlineKeyboardButton("Back to Menu", callback_data="fin_back_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def finance_back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "fin_back_menu":
        await finance(update, context)  # Re-show main menu

def initialize():
    init_db()
    print("[finance_plugin] Initialized – button menu with debug & back buttons")

# Registration in telegram_plugin.py (make sure these are present):
# application.add_handler(CommandHandler("finance", finance))
# application.add_handler(CallbackQueryHandler(finance_callback, pattern=r"^fin_"))
# application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_finance_input))