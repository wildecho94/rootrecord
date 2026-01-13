# Plugin_Files/telegram_plugin.py
# Version: 20260113 – Registered finance, geopy, vehicles plugins + auto-enrichment

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
        print(f"[telegram_plugin] Database ready at: {DB_PATH} (every ping saved)")
    except sqlite3.Error as e:
        print(f"[telegram_plugin] DB ERROR: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def save_gps_record(update: Update):
    msg = update.message or update.edited_message
    if not msg or not msg.location:
        print("[telegram_plugin] No location found - skipping save")
        return False, None

    loc = msg.location
    user = msg.from_user

    # Use already-parsed datetime objects directly
    if update.edited_message and msg.edit_date:
        ping_time = msg.edit_date.isoformat()
        ping_type = "EDIT (live ping)"
    elif msg.date:
        ping_time = msg.date.isoformat()
        ping_type = "NEW"
    else:
        ping_time = datetime.utcnow().isoformat()
        ping_type = "FALLBACK (no date)"

    print(f"[telegram_plugin] Saving {ping_type} for user {user.id} ({user.username or 'no username'}): "
          f"({loc.latitude:.6f}, {loc.longitude:.6f}) @ {ping_time} | Msg ID: {msg.message_id}")

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
            getattr(msg, 'live_period', None), ping_time
        ))
        conn.commit()
        ping_id = cursor.lastrowid
        print(f"[telegram_plugin] SUCCESS: Saved ping (id: {ping_id or 'new'})")
        return True, ping_id
    except sqlite3.Error as e:
        print(f"[telegram_plugin] SAVE FAILED: {e}")
        return False, None
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
# Location handler - catches BOTH new and edited (live) locations + auto-enrich
# ────────────────────────────────────────────────
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[telegram_plugin] Location handler triggered")
    if update.edited_message:
        print("[telegram_plugin] → EDITED message (live location ping)")
    else:
        print("[telegram_plugin] → NEW message")

    saved, ping_id = save_gps_record(update)
    if saved:
        print("[telegram_plugin] Location saved successfully")
        # Auto-enrich with geopy (original timestamp from save)
        if ping_id:
            loc = update.edited_message.location if update.edited_message else update.message.location
            orig_time = update.edited_message.edit_date.isoformat() if update.edited_message and update.edited_message.edit_date else \
                        (update.message.date.isoformat() if update.message.date else datetime.utcnow().isoformat())
            # Simple enrichment (distance needs prev coords - can add later)
            from Plugin_Files.geopy_plugin import enrich_ping
            enrich_ping(ping_id, loc.latitude, loc.longitude, orig_time)
    else:
        print("