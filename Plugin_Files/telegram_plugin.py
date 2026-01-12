# Plugin_Files/telegram_plugin.py
# Version: 1.42.20260112 - VERBOSE + FIXED (full console visibility)

import asyncio
import json
import importlib.util
import logging
import sys
from pathlib import Path
from threading import Thread
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
)

# ────────────────────────────────────────────────
# Force ALL output to console immediately
# ────────────────────────────────────────────────
sys.stdout.reconfigure(line_buffering=True)  # Force line buffering
print = lambda *args, **kwargs: print(*args, **kwargs, flush=True)  # Auto-flush

# ────────────────────────────────────────────────
# Logging - show everything in console
# ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]  # Force to console
)
logger = logging.getLogger("telegram_plugin")
logging.getLogger("telegram").setLevel(logging.INFO)      # Show Telegram lib activity
logging.getLogger("httpx").setLevel(logging.WARNING)      # Reduce httpx noise

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
# Database
# ────────────────────────────────────────────────

import sqlite3

def init_db():
    print("[telegram_plugin] Initializing database...")
    DATA_DIR.mkdir(exist_ok=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                username        TEXT,
                first_name      TEXT,
                last_name       TEXT,
                chat_id         INTEGER NOT NULL,
                message_id      INTEGER,
                latitude        REAL NOT NULL,
                longitude       REAL NOT NULL,
                accuracy        REAL,
                heading         REAL,
                speed           REAL,
                altitude        REAL,
                live_period     INTEGER,
                timestamp       TEXT NOT NULL,
                received_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, user_id) ON CONFLICT IGNORE
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timestamp ON gps_records (user_id, timestamp)')
        conn.commit()
        print(f"[telegram_plugin] Database ready at: {DB_PATH}")
    except sqlite3.Error as e:
        print(f"[telegram_plugin] DB ERROR: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def save_gps_record(update: Update):
    msg = update.message or update.edited_message
    if not msg or not msg.location:
        print("[telegram_plugin] No location in update - skipping save")
        return False

    loc = msg.location
    user = msg.from_user
    timestamp = datetime.utcnow().isoformat()

    print(f"[telegram_plugin] Saving location for user {user.id} ({user.username or 'no username'}): "
          f"({loc.latitude}, {loc.longitude}) @ {timestamp}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gps_records (
                user_id, username, first_name, last_name,
                chat_id, message_id,
                latitude, longitude, accuracy, heading,
                live_period, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.id, user.username, user.first_name, user.last_name,
            msg.chat.id, msg.message_id,
            loc.latitude, loc.longitude, loc.horizontal_accuracy, loc.heading,
            msg.live_period if hasattr(msg, 'live_period') else None,
            timestamp
        ))
        conn.commit()
        print(f"[telegram_plugin] SUCCESS: Saved GPS record for user {user.id}")
        return True
    except sqlite3.Error as e:
        print(f"[telegram_plugin] SAVE FAILED: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

# ────────────────────────────────────────────────
# Command loading
# ────────────────────────────────────────────────

def load_commands(application: Application):
    print("[telegram_plugin] Loading commands from folder...")
    COMMANDS_DIR.mkdir(exist_ok=True)

    start_file = COMMANDS_DIR / "start_cmd.py"
    if not list(COMMANDS_DIR.glob("*_cmd.py")):
        print("[telegram_plugin] No commands found - creating default /start")
        start_file.write_text('''\
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\\n"
        "GPS tracking active. Send a location or live location to record it."
    )

handler = CommandHandler("start", start)
''', encoding='utf-8')

    for path in sorted(COMMANDS_DIR.glob("*_cmd.py")):
        if path.name.startswith("__"): continue
        cmd_name = path.stem.replace("_cmd", "")
        print(f"[telegram_plugin] Attempting to load: /{cmd_name} from {path.name}")
        try:
            spec = importlib.util.spec_from_file_location(f"commands.{path.stem}", path)
            if not spec:
                print(f"[telegram_plugin] Skipped {path.name} - no spec")
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "handler"):
                application.add_handler(module.handler)
                print(f"[telegram_plugin] SUCCESS: Loaded command /{cmd_name}")
            else:
                print(f"[telegram_plugin] WARNING: {path.name} has no 'handler'")
        except Exception as e:
            print(f"[telegram_plugin] FAILED to load {path.name}: {type(e).__name__}: {e}")

# ────────────────────────────────────────────────
# Handlers
# ────────────────────────────────────────────────

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[telegram_plugin] Location update received")
    saved = save_gps_record(update)
    if saved:
        print("[telegram_plugin] Location saved successfully")
    else:
        print("[telegram_plugin] Location save failed")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    await query.message.reply_text(f"You clicked button: {data}")
    print(f"[telegram_plugin] Callback received: {data} from user {query.from_user.id}")

async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        msg = update.message
        text = msg.text or msg.caption or "[no text]"
        prefix = "COMMAND" if text.startswith('/') else "MESSAGE"
        user = msg.from_user
        print(f"[telegram_plugin] {prefix} from {user.username or user.id} (id:{user.id}): {text}")

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

    print("[telegram_plugin] Adding location handler...")
    application.add_handler(MessageHandler(
        filters.LOCATION | filters.LIVE_LOCATION,
        handle_location
    ))

    print("[telegram_plugin] Adding callback query handler...")
    application.add_handler(CallbackQueryHandler(button_callback))

    print("[telegram_plugin] Adding global message logger...")
    application.add_handler(MessageHandler(filters.ALL, log_all))

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