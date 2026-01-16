# Plugin_Files/telegram_plugin.py
# Updated: fixed location handler to use correct attributes (no 'altitude' or 'heading' on Location)

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

from utils.db_mysql import get_db
from sqlalchemy import text

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

# Paths & Config
ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"

print(f"[telegram_plugin] Root path: {ROOT}")

# Database Setup
async def init_db():
    print("[telegram_plugin] Creating/updating gps_records table in MySQL...")
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
                accuracy DOUBLE,
                altitude DOUBLE,
                heading DOUBLE,
                speed DOUBLE,
                live_period INT,
                timestamp DATETIME NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_timestamp (user_id, timestamp),
                INDEX idx_chat_timestamp (chat_id, timestamp)
            )
        '''))
        await session.commit()
    print("[telegram_plugin] GPS records table ready in MySQL")

# Dynamic command loader
def load_commands(application: Application):
    folder = COMMANDS_DIR.resolve()
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
                print(f"[commands] {path.name} missing required 'handler' attribute")
        except Exception as e:
            print(f"[commands] Failed to load {path.name}: {e}")

# Location handler – fixed attributes
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.location:
        return

    loc = update.effective_message.location
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message

    data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "chat_id": chat.id,
        "message_id": msg.message_id,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "accuracy": loc.horizontal_accuracy,
        "altitude": None,  # Location object does NOT have altitude
        "heading": None,   # No heading
        "speed": None,     # No speed
        "live_period": None,
        "timestamp": datetime.utcnow()
    }

    try:
        async for session in get_db():
            await session.execute(text('''
                INSERT INTO gps_records (
                    user_id, username, first_name, last_name, chat_id, message_id,
                    latitude, longitude, accuracy, altitude, heading, speed,
                    live_period, timestamp
                ) VALUES (
                    :user_id, :username, :first_name, :last_name, :chat_id, :message_id,
                    :latitude, :longitude, :accuracy, :altitude, :heading, :speed,
                    :live_period, :timestamp
                )
            '''), data)
            await session.commit()
        logger.info(f"[gps] Saved ping for user {user.id}")
    except Exception as e:
        logger.error(f"[gps] Failed to save location: {e}")

# Message logger
async def log_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        logger.debug(f"Message from {update.effective_user.id}: {update.message.text or '[non-text]'}")

# Bot main
TOKEN = None
application = None

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
    global application
    if not TOKEN:
        print("[telegram_plugin] No valid token → exiting")
        return

    print("[telegram_plugin] Starting bot...")
    application = Application.builder().token(TOKEN).build()

    print("[telegram_plugin] Loading commands...")
    load_commands(application)

    print("[telegram_plugin] Adding handlers...")
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, log_all))

    print("[telegram_plugin] Initializing application...")
    await application.initialize()

    print("[telegram_plugin] Starting bot...")
    await application.start()

    print("[telegram_plugin] Starting polling...")
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,
        timeout=10
    )
    print("[telegram_plugin] Polling active")

    await asyncio.Event().wait()

async def shutdown_bot():
    global application
    if application:
        print("[telegram_plugin] Shutting down bot gracefully...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        print("[telegram_plugin] Bot stopped")

def run_bot():
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("[telegram_plugin] KeyboardInterrupt received")
    except Exception as e:
        print(f"[telegram_plugin] Bot crashed: {e}")
    finally:
        asyncio.run(shutdown_bot())

# Plugin entry
def initialize():
    print("[telegram_plugin] initialize() called")
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())

    if TOKEN:
        print("[telegram_plugin] Launching bot in background thread...")
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
    else:
        print("[telegram_plugin] No token – bot disabled")