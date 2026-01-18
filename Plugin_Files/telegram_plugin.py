# Plugin_Files/telegram_plugin.py
# RootRecord Telegram bot core - polling, commands, location handling
# Token from config_telegram.json, absolute import for start
# Edit: dynamic command loading now inside guard → only runs once

import logging
import asyncio
import importlib.util
import json
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
    Application
)

from utils.db_mysql import engine
from sqlalchemy import text

# Finance handlers
from .finance_plugin import (
    finance_menu,
    button_handler,
    add_record,
    show_quickstats
)

# Absolute import for start
from commands.start_cmd import start

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Paths
ROOT_PATH = Path(__file__).parent.parent
COMMANDS_FOLDER = ROOT_PATH / "commands"
CONFIG_PATH = ROOT_PATH / "config_telegram.json"

# Load bot token
def load_token():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    token = config.get("bot_token")
    if not token:
        raise ValueError("bot_token missing or empty in config_telegram.json")
    return token

BOT_TOKEN = load_token()

# Global app + lock
application: Application = None
_init_lock = asyncio.Lock()

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("[telegram_plugin] DB connection tested")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.location:
        return

    user = update.effective_user
    loc = update.message.location

    async with engine.connect() as conn:
        await conn.execute(text(
            "INSERT INTO gps_records (user_id, latitude, longitude, timestamp) "
            "VALUES (:uid, :lat, :lon, NOW())"
        ), {"uid": user.id, "lat": loc.latitude, "lon": loc.longitude})
        await conn.commit()

    await update.message.reply_text(f"Location logged: {loc.latitude:.6f}, {loc.longitude:.6f}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling update: {context.error}")

async def bot_main():
    global application

    async with _init_lock:
        if application is not None and application.running:
            logger.info("[telegram_plugin] Bot already running - skipping duplicate start")
            return

        logger.info("[telegram_plugin] Building new Application...")
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        # Core handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.LOCATION, handle_location))
        application.add_error_handler(error_handler)

        # Finance handlers
        application.add_handler(CommandHandler("finance", finance_menu))
        application.add_handler(CallbackQueryHandler(button_handler, pattern="^fin_"))
        application.add_handler(MessageHandler(filters.Regex(r'^/finance add '), add_record))
        application.add_handler(MessageHandler(filters.Regex(r'^/finance quickstats'), show_quickstats))

        # Dynamic command loading - ONLY here, once per fresh app creation
        loaded = set()
        for path in sorted(COMMANDS_FOLDER.glob("*_cmd.py")):
            if path.name.startswith('__'):
                continue
            cmd_name = path.stem.replace("_cmd", "")
            if cmd_name in loaded:
                continue
            module_name = f"commands.{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "handler"):
                    application.add_handler(module.handler)
                    logger.info(f"[telegram_plugin] Loaded /{cmd_name}")
                    loaded.add(cmd_name)
                else:
                    logger.warning(f"[telegram_plugin] {path.name} missing 'handler'")
            except Exception as e:
                logger.error(f"[telegram_plugin] Failed loading {path.name}: {e}")

        logger.info("[telegram_plugin] Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        logger.info("[telegram_plugin] Polling active - bot is online and listening")

        while True:
            await asyncio.sleep(3600)

async def shutdown_bot():
    global application
    if application:
        logger.info("[telegram_plugin] Shutting down bot...")
        if application.updater:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await engine.dispose()
    logger.info("[telegram_plugin] Bot shutdown complete")

def initialize():
    asyncio.create_task(init_db())
    asyncio.create_task(bot_main())
    print("[telegram_plugin] Initialized – polling starting")