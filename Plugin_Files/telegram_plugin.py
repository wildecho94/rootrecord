# Plugin_Files/telegram_plugin.py
# Edited Version: 1.42.20260112 (fixed)

"""
Telegram plugin - main entry point with global app exposure
"""

import asyncio
import json
import importlib.util                # ← ADDED THIS
from pathlib import Path
from threading import Thread
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

# Global app instance for other plugins to access
app = None

ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger("telegram_plugin")

TOKEN = None
try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
        TOKEN = config.get("bot_token")
    if TOKEN:
        logger.info("Token loaded successfully")
    else:
        logger.warning("bot_token is empty or missing in config_telegram.json")
except Exception as e:
    logger.error(f"Failed to load config: {e}")

def bootstrap_commands():
    COMMANDS_DIR.mkdir(exist_ok=True)
    start_file = COMMANDS_DIR / "start_cmd.py"
    if not start_file.exists():
        start_file.write_text('''\
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\\n"
        "This is RootRecord bot.\\n"
        "Still early — more features coming."
    )

handler = CommandHandler("start", start)
''', encoding='utf-8')
        logger.info("Created commands/start_cmd.py")

def load_commands(application: Application):
    bootstrap_commands()
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

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        msg = update.message
        user = msg.from_user
        chat = msg.chat
        text = msg.text or msg.caption or "[no text]"
        prefix = "COMMAND" if text.startswith('/') else "MESSAGE"
        logger.info(f"{prefix} from {user.username or user.full_name} (id:{user.id}) in {chat.type} '{chat.title or chat.username or chat.id}': {text}")

async def bot_main():
    global app
    if not TOKEN:
        logger.warning("No valid token → exiting")
        return

    logger.info("Initializing application...")
    app = Application.builder().token(TOKEN).build()

    logger.info("Loading commands...")
    load_commands(app)

    logger.info("Adding global message logger (all updates)...")
    app.add_handler(MessageHandler(filters.ALL, log_update))

    logger.info("Starting bot...")
    await app.initialize()
    await app.start()

    logger.info("Starting polling (drop pending = True)...")
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,
        timeout=10
    )

    logger.info("Polling active – bot should now receive updates")

    # NEW: Trigger late registration for GPS plugin *after* polling has started
    try:
        from Plugin_Files.gps_plugin import late_register
        late_register()
        logger.info("Late GPS plugin registration completed")
    except ImportError:
        logger.info("gps_plugin not present - skipping late registration")
    except Exception as e:
        logger.error(f"Late GPS registration failed: {e}")

    # Keep the event loop alive
    await asyncio.Event().wait()

def initialize():
    if TOKEN:
        logger.info("Launching bot in background thread...")
        Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()
    else:
        logger.warning("No token – telegram disabled")