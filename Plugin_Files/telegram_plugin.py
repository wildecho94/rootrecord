# Plugin_Files/telegram_plugin.py
# Edited Version: 1.42.20260110

import asyncio
import json
import importlib.util
from pathlib import Path
from threading import Thread

from telegram.ext import Application, Update

ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"

def bootstrap_commands():
    """Create commands folder and basic start command if missing"""
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


# Load token
TOKEN = None
try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        TOKEN = json.load(f).get("token")
except Exception:
    pass


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
                print(f"[telegram_plugin] Loaded /{cmd_name}")
        except Exception as e:
            print(f"[telegram_plugin] Failed loading {path.name}: {e}")


async def bot_main():
    if not TOKEN:
        print("[telegram_plugin] No valid token")
        return

    print("[telegram_plugin] Building bot...")
    app = Application.builder().token(TOKEN).build()
    load_commands(app)

    await app.initialize()
    await app.start()
    print("[telegram_plugin] Starting polling...")
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )
    print("[telegram_plugin] Polling active — bot is now live")

    await asyncio.Event().wait()  # keep running


def initialize():
    if TOKEN:
        def target():
            asyncio.run(bot_main())
        Thread(target=target, daemon=True).start()
        print("[telegram_plugin] Telegram polling thread started")