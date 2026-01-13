# RootRecord core.py
# Edited Version: 1.42.20260114

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
import asyncio

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
    print(f"{timestamp} {message}")

    LOGS_FOLDER.mkdir(exist_ok=True)
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{timestamp} {message}\n")

def clear_pycache_folders():
    cleared = 0
    for folder in FOLDERS.values():
        pycache = folder / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache)
            log_debug(f"Removed __pycache__: {pycache}")
            cleared += 1
    log_debug(f"Cleared {cleared} __pycache__ folder(s)")

def backup_system():
    now = datetime.now()
    backup_name = f"startup_{now.strftime('%Y%m%d_%H%M%S')}"
    backup_dir = BACKUPS_FOLDER / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    log_debug(f"Starting backup → {backup_dir}")

    for name, folder in FOLDERS.items():
        if folder.exists():
            dest = backup_dir / name
            shutil.copytree(folder, dest, ignore=shutil.ignore_patterns("*.zip"))
            log_debug(f"Backed up {name} (skipped .zip files)")

    data_dest = backup_dir / "data