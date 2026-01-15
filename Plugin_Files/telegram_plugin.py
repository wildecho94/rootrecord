# Plugin_Files/telegram_plugin.py
# Version: 20260113 – Fixed syntax + full registration of finance, geopy, vehicles, fillup plugins

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
# Paths & Config - load TOKEN at top-level (no DB)
# ────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
COMMANDS_DIR = ROOT / "commands"
CONFIG_PATH = ROOT / "config_telegram.json"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "rootrecord.db"

print(f"[telegram_plugin] Root path: {ROOT}")
print(f"[telegram_plugin] DB path: {DB_PATH}")

TOKEN = None
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    TOKEN = config.get("token")
    print("[telegram_plugin] Token loaded successfully")
except Exception as e:
    print(f"[telegram_plugin] Failed to load token from config: {e}")

# ... (keep all your existing functions: init_db, bot_main, load_commands, handle_location, etc.)

def initialize():
    print("[telegram_plugin] initialize() called")
    if not TOKEN:
        print("[telegram_plugin] No token – bot disabled")
        return

    init_db()  # DB init here, retry-safe in core.py
    print("[telegram_plugin] Launching bot in background thread...")
    Thread(target=asyncio.run, args=(bot_main(),), daemon=True).start()

# No register() needed - commands loaded by cmd_loader