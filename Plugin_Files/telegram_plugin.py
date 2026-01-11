# Plugin_Files/telegram_plugin.py
# Edited Version: 1.42.20260111

import asyncio
import json
import importlib.util
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

ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"

# Logging setup for detailed terminal output
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.DEBUG  # ← DEBUG for maximum visibility
)
logger = logging.getLogger("telegram_plugin")

TOKEN = None
try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
        TOKEN = config.get("bot_token")
    if TOKEN:
        print("[telegram_plugin] Token loaded successfully")
    else:
        print("[telegram_plugin] bot_token is empty or missing in config_telegram.json")
except Exception as e:
    print(f"[telegram_plugin] Failed to load config: {e}")

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
        print("[telegram_plugin] Created commands/start_cmd.py")

def load_commands(app: Application):
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
                app.add_handler(module.handler)
                print(f"[telegram_plugin] Loaded command /{cmd_name}")
            else:
                print(f"[telegram_plugin] {path.name} has no 'handler'")
        except Exception as e:
            print(f"[telegram_plugin] Failed to load {path.name}: {type(e).__name__}: {e}")

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming update with full details"""
    if update:
        print(f"[telegram DEBUG] Received update: {update.to_dict()}")
    if update.message:
        msg = update.message
        user = msg.from_user
        chat = msg.chat
        text = msg.text or msg.caption or "[no text/content]"
        prefix = "COMMAND" if text.startswith('/') else "MESSAGE"
        print(f"[telegram] {prefix} from {user.username or user.full_name} "
              f"(id:{user.id}) in {chat.type} '{chat.title or chat.username or chat.id}': {text}")

async def bot_main():
    if not TOKEN:
        print("[telegram_plugin] No valid token → exiting")
        return

    print("[telegram_plugin] Initializing application...")
    app = Application.builder().token(TOKEN).build()

    print("[telegram_plugin] Loading commands...")
    load_commands(app)

    print("[telegram_plugin] Adding global message logger (all updates)...")
    app.add_handler(MessageHandler(filters.ALL, log_update))

    print("[telegram_plugin] Starting bot...")
    await app.initialize()
    await app.start()

    print("[telegram_plugin] Starting polling (drop pending = True)...")
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5,      # faster polling for debugging
        timeout=10
    )

    print("[telegram_plugin] Polling active – bot should now receive updates")
    await asyncio.Event().wait()

def initialize():
    if TOKEN:
        print("[telegram_plugin] Launching bot in background thread...")
        Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()
    else:
        print("[telegram_plugin] No token – telegram disabled")