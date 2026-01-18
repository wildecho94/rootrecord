# Plugin_Files/finance_plugin.py
# Finance plugin for RootRecord - tracks income, expenses, debts, assets
# Fixed: 'text' always defined in every code path in show_* handlers
# Categories auto-create with type guessing
# Commands: /finance (menu), /finance quickstats, /finance add <category> <amount> [desc]

import asyncio
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy import text
from utils.db_mysql import get_db, init_mysql

ROOT = Path(__file__).parent.parent

async def init_db():
    print("[finance_plugin] Creating/updating finance tables and view...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS finance_categories (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name VARCHAR(100) NOT NULL,
                type ENUM('income', 'expense', 'debt', 'asset') NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_user_category (user_id, name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''))

        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                category_id BIGINT NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                description TEXT,
                record_date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_date (user_id, record_date),
                INDEX idx_category (category_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''))

        await session.execute(text('''
            CREATE OR REPLACE VIEW finance_summary AS
            SELECT 
                r.user_id,
                SUM(CASE WHEN c.type IN ('income', 'asset')   THEN r.amount ELSE 0       END) AS total_positive,
                SUM(CASE WHEN c.type IN ('expense', 'debt')  THEN r.amount ELSE 0       END) AS total_negative,
                SUM(CASE WHEN c.type IN ('income', 'asset')  THEN r.amount ELSE -r.amount END) AS current_balance,
                SUM(CASE WHEN c.type IN ('income', 'asset')  THEN r.amount ELSE -r.amount END) AS net_worth
            FROM finance_records r
            JOIN finance_categories c ON r.category_id = c.id
            GROUP BY r.user_id;
        '''))

        await session.commit()
    print("[finance_plugin] Finance tables + summary view ready")

# Category guessing
CATEGORY_TYPE_MAP = {
    'salary': 'income', 'paycheck': 'income', 'bonus': 'income',
    'rent': 'expense', 'groceries': 'expense', 'fuel': 'expense', 'gas': 'expense',
    'coffee': 'expense', 'food': 'expense', 'dinner': 'expense',
    'loan': 'debt', 'credit': 'debt', 'borrow': 'debt',
    'savings': 'asset', 'investment': 'asset', 'crypto': 'asset', 'stock': 'asset'
}

def guess_category_type(name: str) -> str:
    name_lower = name.lower()
    for keyword, cat_type in CATEGORY_TYPE_MAP.items():
        if keyword in name_lower:
            return cat_type
    return 'expense'

async def get_or_create_category(session, user_id: int, cat_name: str) -> int:
    cat_type = guess_category_type(cat_name)
    result = await session.execute(text('''
        SELECT id FROM finance_categories 
        WHERE user_id = :uid AND name = :name
    '''), {"uid": user_id, "name": cat_name})
    row = result.fetchone()
    if row:
        return row[0]

    await session.execute(text('''
        INSERT INTO finance_categories (user_id, name, type)
        VALUES (:uid, :name, :type)
    '''), {"uid": user_id, "name": cat_name, "type": cat_type})
    await session.commit()
    result = await session.execute(text("SELECT LAST_INSERT_ID()"))
    return result.scalar()

# Handlers
async def finance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Quick Stats", callback_data="fin_quickstats")],
        [InlineKeyboardButton("Add Record", callback_data="fin_add")],
        [InlineKeyboardButton("View Categories", callback_data="fin_categories")],
        [InlineKeyboardButton("Balance", callback_data="fin_balance")],
        [InlineKeyboardButton("Net Worth", callback_data="fin_networth")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Finance Dashboard", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "fin_quickstats":
        await show_quickstats(query, context)
    elif data == "fin_add":
        await query.edit_message_text("Send: /finance add <category> <amount> [description]")
    elif data == "fin_categories":
        await show_categories(query, context)
    elif data == "fin_balance":
        await show_balance(query, context)
    elif data == "fin_networth":
        await show_networth(query, context)

async def add_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /finance add <category> <amount> [description]")
        return

    cat_name = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number")
        return

    desc = " ".join(args[2:]) if len(args) > 2 else None
    record_date = datetime.now().date()

    async for session in get_db():
        cat_id = await get_or_create_category(session, user_id, cat_name)
        await session.execute(text('''
            INSERT INTO finance_records 
            (user_id, category_id, amount, description, record_date)
            VALUES (:uid, :cat_id, :amt, :desc, :date)
        '''), {
            "uid": user_id,
            "cat_id": cat_id,
            "amt": amount,
            "desc": desc,
            "date": record_date
        })
        await session.commit()

    await update.message.reply_text(f"Record added: {cat_name} ${amount:,.2f}")

async def show_quickstats(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(query_or_update, 'message'):
        message = query_or_update.message
        user_id = query_or_update.from_user.id
    else:
        message = query_or_update
        user_id = message.chat.id

    async for session in get_db():
        result = await session.execute(text('''
            SELECT current_balance, total_positive, total_negative, net_worth
            FROM finance_summary WHERE user_id = :uid
        '''), {"uid": user_id})
        row = result.fetchone()
        if row and row[0] is not None:
            bal, pos, neg, nw = row
            text = (
                f"**Quick Stats**\n"
                f"Balance: **${bal:,.2f}**\n"
                f"Income+Assets: **${pos:,.2f}**\n"
                f"Expenses+Debts: **${neg:,.2f}**\n"
                f"Net Worth: **${nw:,.2f}**"
            )
        else:
            text = "No records yet. Add one with /finance add"

    if hasattr(message, 'reply_text'):
        await message.reply_text(text, parse_mode="Markdown")
    else:
        await message.edit_text(text, parse_mode="Markdown")

async def show_categories(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(query_or_update, 'message'):
        message = query_or_update.message
        user_id = query_or_update.from_user.id
    else:
        message = query_or_update
        user_id = message.chat.id

    async for session in get_db():
        result = await session.execute(text('''
            SELECT name, type FROM finance_categories WHERE user_id = :uid
        '''), {"uid": user_id})
        cats = result.fetchall()
        if cats:
            text = "**Your Categories**\n" + "\n".join(f"• {c[0]} ({c[1]})" for c in cats)
        else:
            text = "No categories yet — add your first record!"

    if hasattr(message, 'reply_text'):
        await message.reply_text(text, parse_mode="Markdown")
    else:
        await message.edit_text(text, parse_mode="Markdown")

async def show_balance(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(query_or_update, 'message'):
        message = query_or_update.message
        user_id = query_or_update.from_user.id
    else:
        message = query_or_update
        user_id = message.chat.id

    async for session in get_db():
        result = await session.execute(text('''
            SELECT current_balance FROM finance_summary WHERE user_id = :uid
        '''), {"uid": user_id})
        row = result.fetchone()
        if row and row[0] is not None:
            text = f"💰 Current Balance: **${row[0]:,.2f}**"
        else:
            text = "No records yet."

    if hasattr(message, 'reply_text'):
        await message.reply_text(text, parse_mode="Markdown")
    else:
        await message.edit_text(text, parse_mode="Markdown")

async def show_networth(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(query_or_update, 'message'):
        message = query_or_update.message
        user_id = query_or_update.from_user.id
    else:
        message = query_or_update
        user_id = message.chat.id

    async for session in get_db():
        result = await session.execute(text('''
            SELECT net_worth FROM finance_summary WHERE user_id = :uid
        '''), {"uid": user_id})
        row = result.fetchone()
        if row and row[0] is not None:
            text = f"🌐 Net Worth: **${row[0]:,.2f}**"
        else:
            text = "No records yet."

    if hasattr(message, 'reply_text'):
        await message.reply_text(text, parse_mode="Markdown")
    else:
        await message.edit_text(text, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[finance_plugin] Initialized – /finance menu + summary view ready")