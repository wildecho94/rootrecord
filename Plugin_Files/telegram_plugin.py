# Plugin_Files/telegram_plugin.py
# Version: 20260117 – Fixed finance callback registration + verbose debug

import asyncio
import json
import importlib.util
import logging
from pathlib import Path
from threading import Thread
from datetime import datetime
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
)

# ────────────────────────────────────────────────
# Logging - very verbose for debugging
# ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("telegram_plugin")
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
print("[telegram_plugin] Logging initialized - VERBOSE mode ON")

# ────────────────────────────────────────────────
# Paths & Config
# ────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "rootrecord.db"

print(f"[telegram_plugin] Root path: {ROOT}")
print(f"[telegram_plugin] DB path: {DB_PATH}")

# ────────────────────────────────────────────────
# Database - immediate save on EVERY ping
# ────────────────────────────────────────────────
def init_db():
    print("[telegram_plugin] Initializing database...")
    DATA_DIR.mkdir(exist_ok=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                chat_id INTEGER NOT NULL,
                message_id INTEGER,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                heading REAL,
                speed REAL,
                altitude REAL,
                live_period INTEGER,
                timestamp TEXT NOT NULL,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timestamp ON gps_records (user_id, timestamp)')
        conn.commit()
        print(f"[telegram_plugin] GPS table ready")
    except Exception as e:
        print(f"[telegram_plugin] DB init error: {e}")

# ────────────────────────────────────────────────
# Handlers
# ────────────────────────────────────────────────

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    user = update.effective_user
    print(f"[tel] Location from {user.id} ({user.username}): {loc.latitude}, {loc.longitude}")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO gps_records (
                user_id, username, first_name, last_name, chat_id, message_id,
                latitude, longitude, accuracy, heading, speed, altitude,
                live_period, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.id, user.username, user.first_name, user.last_name,
            update.effective_chat.id, update.message.message_id,
            loc.latitude, loc.longitude, loc.horizontal_accuracy,
            loc.heading, loc.speed, loc.altitude,
            update.message.live_period,
            update.message.date.isoformat()
        ))
        conn.commit()
    print(f"[tel] Saved ping {c.lastrowid}")

async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[tel] Message: {update.message.text if update.message.text else '[non-text]'} "
          f"from {update.effective_user.username} ({update.effective_user.id})")

# ────────────────────────────────────────────────
# Plugin registration helpers
# ────────────────────────────────────────────────

def load_commands(application: Application):
    folder = Path(__file__).parent.parent / "commands"
    for path in sorted(folder.glob("*_cmd.py")):
        if path.name.startswith('__'):
            continue
        cmd_name = path.stem.replace("_cmd", "")
        module_name = f"commands.{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "handler"):
                application.add_handler(module.handler)
                print(f"[commands] Loaded /{cmd_name}")
            else:
                print(f"[commands] {path.name} missing 'handler'")
        except Exception as e:
            print(f"[commands] Failed to load {path.name}: {e}")

def register_new_plugins(application: Application):
    print("[telegram_plugin] Registering new plugins...")

    # Finance plugin – menu + callbacks + input
    from Plugin_Files.finance_plugin import (
        finance, finance_callback, handle_finance_input
    )
    print("[telegram_plugin] Registering /finance with buttons...")
    application.add_handler(CommandHandler("finance", finance))
    application.add_handler(CallbackQueryHandler(finance_callback, pattern=r"^fin_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_finance_input))
    print("[telegram_plugin] /finance fully registered (command + callback + input)")

    # Vehicles management
    from Plugin_Files.vehicles_plugin import (
        cmd_vehicle_add, cmd_vehicles, callback_vehicle_menu
    )
    application.add_handler(CommandHandler("vehicle", cmd_vehicle_add))
    application.add_handler(CommandHandler("vehicles", cmd_vehicles))
    application.add_handler(CallbackQueryHandler(callback_vehicle_menu, pattern="^veh_"))
    print("[telegram_plugin] Vehicles management registered")

    # Fillup plugin
    from Plugin_Files.fillup_plugin import (
        cmd_fillup, handle_fillup_input, callback_fillup_confirm
    )
    application.add_handler(CommandHandler("fillup", cmd_fillup))
    application.add_handler(CallbackQueryHandler(callback_fillup_confirm, pattern="^fillup_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_fillup_input))
    print("[telegram_plugin] Fillup plugin registered")

# ────────────────────────────────────────────────
# Main bot startup
# ────────────────────────────────────────────────
TOKEN = None
try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
        TOKEN = config.get("bot_token")
    if TOKEN:
        print("[telegram_plugin] Token loaded successfully")
    else:
        print("[telegram_plugin] WARNING: bot_token missing in config_telegram.json")
except Exception as e:
    print(f"[telegram_plugin] Config load failed: {e}")

async def bot_main():
    if not TOKEN:
        print("[telegram_plugin] No valid token → exiting")
        return

    print("[telegram_plugin] Starting bot...")
    application = Application.builder().token(TOKEN).build()

    print("[telegram_plugin] Loading commands...")
    load_commands(application)

    print("[telegram_plugin] Registering new plugins...")
    register_new_plugins(application)

    print("[telegram_plugin] Adding location handler (new + edited messages)...")
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.LOCATION, handle_location))

    print("[telegram_plugin] Adding global message logger...")
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, log_all))

    print("[telegram_plugin] Initializing application...")
    await application.initialize()
    print("[telegram_plugin] Application initialized")

    print("[telegram_plugin] Starting bot...")
    await application.start()
    print("[telegram_plugin] Bot started")

    print("[telegram_plugin] Starting polling...")
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,
        timeout=10
    )
    print("[telegram_plugin] Polling active – full activity should now be visible")

    await asyncio.Event().wait()

def initialize():
    print("[telegram_plugin] initialize() called")
    init_db()
    if TOKEN:
        print("[telegram_plugin] Launching bot in background thread...")
        Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()
    else:
        print("[telegram_plugin] No token – bot disabled")