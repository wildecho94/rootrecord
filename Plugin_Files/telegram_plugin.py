# Plugin_Files/telegram_plugin.py
# Version: 1.42.20260117 – Full Telegram bot integration
# Fixed: Added geopy enrichment trigger after every location save
#        Uses lastrowid to get ping_id and queues async enrich_ping task
#        Cleaned altitude handling (Telegram provides none)
#        Keeps verbose logging, polling, command loading, shutdown dispose

import asyncio
import json
import importlib.util
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from utils.db_mysql import get_db, engine
from sqlalchemy import text

# Import geopy enrichment function
# Assumption: geopy_plugin.py defines async def enrich_ping(ping_id: int, lat: float, lon: float)
from Plugin_Files.geopy_plugin import enrich_ping

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("telegram_plugin")
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
print("[telegram_plugin] Logging initialized - VERBOSE mode ON")

ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"

print(f"[telegram_plugin] Root path: {ROOT}")

async def init_db():
    print("[telegram_plugin] Creating/updating gps_records table...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                chat_id BIGINT NOT NULL,
                message_id INT,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                accuracy FLOAT,
                heading FLOAT,
                altitude FLOAT,
                altitude_accuracy FLOAT,
                timestamp DATETIME NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        await session.commit()

        try:
            await session.execute(text('''
                CREATE INDEX idx_user_timestamp ON gps_records (user_id, timestamp)
            '''))
            await session.commit()
            print("[telegram_plugin] Created index idx_user_timestamp")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print("[telegram_plugin] Index idx_user_timestamp already exists")
            else:
                print(f"[telegram_plugin] Index creation failed: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.effective_message.location
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message

    lat = loc.latitude
    lon = loc.longitude
    print(f"[gps] Received location: lat={lat:.6f}, lon={lon:.6f}")

    ping_id = None
    async for session in get_db():
        result = await session.execute(text('''
            INSERT INTO gps_records (
                user_id, username, first_name, last_name,
                chat_id, message_id,
                latitude, longitude, accuracy, heading,
                altitude, altitude_accuracy,
                timestamp
            ) VALUES (
                :user_id, :username, :first_name, :last_name,
                :chat_id, :message_id,
                :latitude, :longitude, :accuracy, :heading,
                :altitude, :altitude_accuracy,
                :timestamp
            )
        '''), {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "chat_id": chat.id,
            "message_id": msg.message_id,
            "latitude": lat,
            "longitude": lon,
            "accuracy": loc.horizontal_accuracy,
            "heading": loc.heading,
            "altitude": None,               # Telegram Location has no altitude
            "altitude_accuracy": None,
            "timestamp": datetime.utcnow().isoformat()
        })
        await session.commit()

        ping_id = result.lastrowid
        print(f"[gps] Saved ping id={ping_id} for user {user.id}")

    # Trigger geopy enrichment in background on every successful save
    if ping_id:
        asyncio.create_task(enrich_ping(ping_id, lat, lon))
        print(f"[gps] Queued geopy enrichment task for ping {ping_id}")

async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = msg.text or "[non-text message]"
    print(f"[telegram_plugin] Received from {update.effective_user.id}: {text}")

def load_commands(application: Application):
    folder = COMMANDS_DIR
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
                print(f"[telegram_plugin] Loaded /{cmd_name}")
            else:
                print(f"[telegram_plugin] {path.name} missing 'handler'")
        except Exception as e:
            print(f"[telegram_plugin] Failed to load {path.name}: {e}")

config = {}
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"[telegram_plugin] Config load failed: {e}")

TOKEN = config.get("bot_token")
if not TOKEN:
    print("[telegram_plugin] Missing bot_token in config_telegram.json – bot disabled")

application = None

async def bot_main():
    global application
    if not TOKEN:
        print("[telegram_plugin] No token – skipping bot_main")
        return

    print("[telegram_plugin] Building application...")
    application = Application.builder().token(TOKEN).build()

    print("[telegram_plugin] Loading commands...")
    load_commands(application)

    print("[telegram_plugin] Adding handlers...")
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_all))

    print("[telegram_plugin] Initializing...")
    await application.initialize()

    print("[telegram_plugin] Starting...")
    await application.start()

    print("[telegram_plugin] Polling...")
    await application.updater.start_polling(
        drop_pending_updates=True,
        poll_interval=0.5,
        timeout=10
    )
    print("[telegram_plugin] Polling active")

    await asyncio.Event().wait()

async def shutdown_bot():
    global application
    if application:
        print("[telegram_plugin] Shutting down bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await engine.dispose()
        print("[telegram_plugin] Engine disposed, connections returned to pool")

def initialize():
    print("[telegram_plugin] initialize() called")
    asyncio.create_task(init_db())
    print("[telegram_plugin] Ready – call bot_main() to start")