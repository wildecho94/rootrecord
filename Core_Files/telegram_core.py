# Plugin_Files/telegram_core.py
# Combined Telegram bot + GPS location saving + callback handler
# Version: 1.42.20260112 (final merged core with callback support)

import asyncio
import json
import importlib.util
import logging
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
# Logging setup
# ────────────────────────────────────────────────

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger("telegram_core")

# ────────────────────────────────────────────────
# Paths & Config
# ────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "rootrecord.db"

# ────────────────────────────────────────────────
# Database (embedded)
# ────────────────────────────────────────────────

import sqlite3

def init_db():
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
        logger.info(f"Database ready at: {DB_PATH}")
        print(f"[telegram_core] DB initialized at {DB_PATH}")
    except sqlite3.Error as e:
        logger.error(f"DB init failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def save_gps_record(update: Update):
    msg = update.message or update.edited_message
    if not msg or not msg.location:
        return False

    loc = msg.location
    user = msg.from_user
    timestamp = datetime.utcnow().isoformat()

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
        logger.info(f"Saved GPS for user {user.id} → ({loc.latitude}, {loc.longitude})")
        print(f"[telegram_core] Saved location for {user.username or user.id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Save failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

# ────────────────────────────────────────────────
# Command loading
# ────────────────────────────────────────────────

def load_commands(application: Application):
    COMMANDS_DIR.mkdir(exist_ok=True)

    start_file = COMMANDS_DIR / "start_cmd.py"
    if not COMMANDS_DIR.glob("*_cmd.py"):
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
        logger.info("Created default commands/start_cmd.py")

    for path in sorted(COMMANDS_DIR.glob("*_cmd.py")):
        if path.name.startswith("__"): continue
        cmd_name = path.stem.replace("_cmd", "")
        try:
            spec = importlib.util.spec_from_file_location(f"commands.{path.stem}", path)
            if not spec: continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "handler"):
                application.add_handler(module.handler)
                logger.info(f"Loaded command /{cmd_name}")
            else:
                logger.warning(f"{path.name} has no 'handler'")
        except Exception as e:
            logger.error(f"Failed to load {path.name}: {type(e).__name__}: {e}")

# ────────────────────────────────────────────────
# Handlers
# ────────────────────────────────────────────────

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    saved = save_gps_record(update)
    if saved:
        # Optional: reply
        # await update.message.reply_text("Location saved!")
        pass

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processes inline button clicks (moved from telegram_handler.py)
    """
    query = update.callback_query
    await query.answer()  # Acknowledge
    data = query.data
    await query.message.reply_text(f"You clicked button: {data}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Callback received: {data} from user {query.from_user.id}")

# ────────────────────────────────────────────────
# Main bot startup
# ────────────────────────────────────────────────

TOKEN = None
try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
        TOKEN = config.get("bot_token")
    if TOKEN:
        logger.info("Token loaded successfully")
    else:
        logger.warning("bot_token missing in config_telegram.json")
except Exception as e:
    logger.error(f"Failed to load config: {e}")

async def bot_main():
    if not TOKEN:
        logger.warning("No valid token → exiting")
        return

    logger.info("Starting Telegram core with GPS + callbacks...")
    application = Application.builder().token(TOKEN).build()

    # Load commands
    load_commands(application)

    # Location handler
    application.add_handler(MessageHandler(
        filters.LOCATION | filters.LIVE_LOCATION,
        handle_location
    ))

    # Inline button callback handler (from old telegram_handler.py)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Global message logger (optional)
    async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            msg = update.message
            text = msg.text or msg.caption or "[no text]"
            prefix = "COMMAND" if text.startswith('/') else "MESSAGE"
            logger.info(f"{prefix} from {msg.from_user.username or msg.from_user.id}: {text}")
    application.add_handler(MessageHandler(filters.ALL, log_message))

    logger.info("Initializing application...")
    await application.initialize()
    await application.start()

    logger.info("Starting polling (drop pending = True)...")
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,
        timeout=10
    )

    logger.info("Polling active – GPS tracking & callbacks ready")
    await asyncio.Event().wait()

def initialize():
    init_db()
    if TOKEN:
        logger.info("Launching Telegram core in background...")
        Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()
    else:
        logger.warning("No token – Telegram disabled")