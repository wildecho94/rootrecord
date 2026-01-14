# RootRecord core.py
# Edited Version: 1.42.20260114

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # Add project root to import path

import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
import asyncio

# Enable WAL mode globally for better concurrency
def connect_with_wal(*args, **kwargs):
    conn = sqlite3.connect(*args, **kwargs)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# Replace default connect (safe, no lambda conflict)
sqlite3.connect = connect_with_wal

BASE_DIR = Path(__file__).parent

CORE_FOLDER    = BASE_DIR / "Core_Files"
HANDLER_FOLDER = BASE_DIR / "Handler_Files"
PLUGIN_FOLDER  = BASE_DIR / "Plugin_Files"

FOLDERS = {
    "core":    CORE_FOLDER,
    "handler": HANDLER_FOLDER,
    "plugin":  PLUGIN_FOLDER
}

LOGS_FOLDER = BASE_DIR / "logs"
DEBUG_LOG   = LOGS_FOLDER / "debug_rootrecord.log"
DATA_FOLDER = BASE_DIR / "data"
BACKUPS_FOLDER = BASE_DIR / "backups"

def log_debug(message):
    now = datetime.now()
    timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    full_message = f"{timestamp} {message}"
    print(full_message)

    LOGS_FOLDER.mkdir(exist_ok=True)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

def clear_pycache_folders():
    cleared = 0
    for folder in FOLDERS.values():
        pycache = folder / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache)
            log_debug(f"Removed __pycache__: