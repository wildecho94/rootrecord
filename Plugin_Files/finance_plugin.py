# Plugin_Files/finance_plugin.py
# Version: 1.43.20260117 – Migrated to PostgreSQL (async, single DB, no locks)

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from core.db_postgres import get_db, init_postgres  # Shared Postgres helper

ROOT = Path(__file__).parent.parent

async def init_db(session):
    print("[finance_plugin] Creating/updating finance_records table in PostgreSQL...")
    await session.execute(text('''
        CREATE TABLE IF NOT EXISTS finance_records (
            id SERIAL PRIMARY KEY,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'Uncategorized',
            timestamp TIMESTAMP NOT NULL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vehicle_id INTEGER
        )
    '''))
    await session.execute(text('CREATE INDEX IF NOT EXISTS idx_type_timestamp ON finance_records (type, timestamp)'))
    print("[finance_plugin] Finance table ready in PostgreSQL")

async def log_entry(type_: str, amount: float, desc: str, cat: str = None, vehicle_id: int = None):
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO finance_records (type, amount, description, category, timestamp, vehicle_id)
            VALUES (:type, :amount, :description, :category, :timestamp, :vehicle_id)
        '''), {
            "type": type_,
            "amount": amount,
            "description": desc,
            "category": cat,
            "timestamp": datetime.utcnow(),
            "vehicle_id": vehicle_id
        })
        await session.commit()
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
            await log_entry(sub, amount, desc, cat)
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
        "Finance Menu\nWhat would you like to do?",
        reply_markup=reply_markup
    )

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id
    print(f"[finance callback DEBUG] User {user_id} tapped button: {data}")

    if data == "fin_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data.pop(f"fin_pending_{user_id}", None)
        return

    if data == "fin_menu":
        await finance(update, context)
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

    await log_entry(entry_type, amount, desc, cat)
    await update.message.reply_text(
        f"✅ **{entry_type.capitalize()}** of **${amount:.2f}** logged: {desc}",
        parse_mode="Markdown"
    )

    context.user_data.pop(pending_key, None)

async def show_detailed_report(update: Update, context: ContextTypes.DEFAULT_TYPE, is_balance: bool):
    async for session in get_db():
        total_income = (await session.execute(text("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type = 'income'"))).scalar()
        total_expense = (await session.execute(text("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type = 'expense'"))).scalar()
        total_assets = (await session.execute(text("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type = 'asset'"))).scalar()
        total_debt = (await session.execute(text("SELECT COALESCE(SUM(amount), 0) FROM finance_records WHERE type = 'debt'"))).scalar()

        balance = total_income - total_expense
        net_worth = (total_income + total_assets) - (total_expense + total_debt)

        top_exp = await session.execute(text('''
            SELECT category, SUM(amount) as total
            FROM finance_records
            WHERE type = 'expense' AND category IS NOT NULL
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        '''))
        top_exp = top_exp.fetchall()

        recent = await session.execute(text('''
            SELECT type, amount, description, category, timestamp
            FROM finance_records
            ORDER BY id DESC
            LIMIT 5
        '''))
        recent = recent.fetchall()

    title = "Balance Report" if is_balance else "Net Worth Report"
    main_val = balance if is_balance else net_worth
    main_lbl = "Current Balance" if is_balance else "Current Net Worth"

    text = f"**{title}**\n\n"
    text += f"**{main_lbl}**: **${main_val:,.2f}**\n\n"

    text += "**Overview**\n"
    text += f"• Total Income: **${total_income:,.2f}**\n"
    text += f"• Total Expenses: **${total_expense:,.2f}**\n"
    text += f"• Total Assets: **${total_assets:,.2f}**\n"
    text += f"• Total Debts: **${total_debt:,.2f}**\n\n"

    if top_exp:
        text += "**Top Expense Categories**\n"
        for cat, amt in top_exp:
            text += f"• {cat or 'Uncategorized'}: **${amt:,.2f}**\n"
        text += "\n"
    else:
        text += "**No categorized expenses yet.**\n\n"

    if recent:
        text += "**Recent Activity (last 5)**\n"
        for typ, amt, desc, cat, ts in recent:
            cat_str = f" ({cat})" if cat and cat != 'Uncategorized' else ""
            text += f"• {typ.capitalize()} ${amt:,.2f}{cat_str} – {desc[:50]}{'...' if len(desc)>50 else ''} ({ts.date()})\n"
    else:
        text += "**No transactions logged yet.**\n"

    keyboard = [
        [InlineKeyboardButton("Back to Menu", callback_data="fin_menu")],
        [InlineKeyboardButton("Close", callback_data="fin_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_postgres())
    print("[finance_plugin] Initialized – PostgreSQL version")