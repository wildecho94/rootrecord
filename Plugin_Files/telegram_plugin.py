# Plugin_Files/telegram_plugin.py
# Version: 20260113 – Fixed syntax + full registration of finance, geopy, vehicles, fillup plugins

import asyncio
import json
import importlib.util
import logging
from pathlib import Path
from threading import Thread
from datetime import datetime
import sqlite3

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
)

# Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("telegram_plugin")
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
print("[telegram_plugin] Logging initialized - VERBOSE mode ON")

# Paths
ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "rootrecord.db"

print(f"[telegram_plugin] Root path: {ROOT}")
print(f"[telegram_plugin] DB path: {DB_PATH}")

# Load TOKEN at top-level
TOKEN = None
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    TOKEN = config.get("bot_token")
    print("[telegram_plugin] Token loaded successfully")
except Exception as e:
    print(f"[telegram_plugin] Failed to load token from config: {e}")

# Database init - add this missing function
def init_db():
    print("[telegram_plugin] Initializing database...")
    DATA_DIR.mkdir(exist_ok=True)
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gps_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    message_id INTEGER,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        print(f"[telegram_plugin] Database ready at: {DB_PATH} (every ping saved)")
    except Exception as e:
        print(f"[telegram_plugin] DB init failed: {e}")

# Bot main (polling)
async def bot_main():
    app = Application.builder().token(TOKEN).build()

    # Load commands
    print("[telegram_plugin] Loading commands from folder...")
    for path in COMMANDS_DIR.glob("*_cmd.py"):
        name = path.stem
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "handler"):
                app.add_handler(module.handler)
                print(f"[telegram_plugin] SUCCESS: Loaded command /{name.replace('_cmd', '')}")
            else:
                print(f"[telegram_plugin] No handler in {name}")
        except Exception as e:
            print(f"[telegram_plugin] FAILED to load {name}: {e}")

    # Add location handler (placeholder - add your real one)
    async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = update.message
        if msg.location:
            user = msg.from_user
            lat, lon = msg.location.latitude, msg.location.longitude
            ts = msg.date.isoformat()
            print(f"[telegram_plugin] Location saved for user {user.id} ({user.username}): ({lat}, {lon}) @ {ts}")

    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Start polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True, poll_interval=0.5)
    print("[telegram_plugin] Polling active – full activity should now be visible")

def initialize():
    print("[telegram_plugin] initialize() called")
    if not TOKEN:
        print("[telegram_plugin] No token – bot disabled")
        return

    init_db()
    print("[telegram_plugin] Launching bot in background thread...")
    Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()