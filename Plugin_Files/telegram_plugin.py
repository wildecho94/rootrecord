# Plugin_Files/telegram_plugin.py
# Version: 20260113 – Fixed syntax + full registration of finance, geopy, vehicles plugins

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
        "GPS tracking active. Send a location or live location to record it.\\n"
        "Use /vehicles for car management, /finance for money tracking."
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
# Location handler - auto-enrich with geopy
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
        if ping_id:
            loc = update.edited_message.location if update.edited_message else update.message.location
            orig_time = update.edited_message.edit_date.isoformat() if update.edited_message and update.edited_message.edit_date else \
                        (update.message.date.isoformat() if update.message.date else datetime.utcnow().isoformat())
            from Plugin_Files.geopy_plugin import enrich_ping
            enrich_ping(ping_id, loc.latitude, loc.longitude, orig_time)
    else:
        print("[telegram_plugin] Location save failed")

async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        msg = update.message
        text = msg.text or msg.caption or "[no text]"
        prefix = "COMMAND" if text.startswith('/') else "MESSAGE"
        user = msg.from_user
        print(f"[telegram_plugin] {prefix} from {user.username or user.id} (id:{user.id}): {text}")

# ────────────────────────────────────────────────
# Register new plugins' commands & hooks
# ────────────────────────────────────────────────
def register_new_plugins(application: Application):
    print("[telegram_plugin] Registering new plugins...")

    # Finance plugin
    try:
        from Plugin_Files.finance_plugin import finance
        application.add_handler(CommandHandler("finance", finance))
        print("[telegram_plugin] /finance registered")
    except ImportError as e:
        print(f"[telegram_plugin] Finance plugin import failed: {e}")
    except Exception as e:
        print(f"[telegram_plugin] Finance plugin registration error: {e}")

    # Vehicles plugin (full suite) – split to avoid one missing function killing everything
    try:
        from Plugin_Files.vehicles_plugin import (
            cmd_vehicle_add,
            cmd_vehicles,
            cmd_fillup,
            cmd_mpg,
            callback_vehicle_menu,
            callback_fill,
            handle_fillup_input
        )
        print("[telegram_plugin] Vehicles functions imported successfully")

        # Register handlers one by one
        application.add_handler(CommandHandler("vehicle", cmd_vehicle_add))
        application.add_handler(CommandHandler("vehicles", cmd_vehicles))
        application.add_handler(CommandHandler("fillup", cmd_fillup))
        application.add_handler(CommandHandler("mpg", cmd_mpg))
        application.add_handler(CallbackQueryHandler(callback_vehicle_menu, pattern="^veh_"))
        application.add_handler(CallbackQueryHandler(callback_fill, pattern="^veh_fill_"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fillup_input))

        print("[telegram_plugin] Vehicles commands + buttons registered (all handlers added)")
    except ImportError as e:
        print(f"[telegram_plugin] Vehicles import failed: {e}")
        print("    → Check that vehicles_plugin.py contains: cmd_vehicle_add, cmd_vehicles, cmd_fillup, cmd_mpg, callback_vehicle_menu, callback_fill, handle_fillup_input")
    except Exception as e:
        print(f"[telegram_plugin] Vehicles registration error: {e}")

    # Geopy is auto-called from handle_location (no extra registration needed)

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fillup_input))

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