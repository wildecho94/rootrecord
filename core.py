# RootRecord core.py
# Version: 1.43.20260116 – Fixed async plugin init (loop starts first), lowercase utils folder
# Backup completely removed (no sqlite or other backups)

from pathlib import Path
import sys
import os
from datetime import datetime
import sqlite3
import importlib.util
import asyncio
import time

BASE_DIR = Path(__file__).parent

UTILS_FOLDER   = BASE_DIR / "utils"
PLUGIN_FOLDER  = BASE_DIR / "Plugin_Files"

FOLDERS = {
    "utils":   UTILS_FOLDER,
    "plugin":  PLUGIN_FOLDER
}

LOGS_FOLDER = BASE_DIR / "logs"
DEBUG_LOG   = LOGS_FOLDER / "debug_rootrecord.log"
DATA_FOLDER = BASE_DIR / "data"
DATABASE    = DATA_FOLDER / "rootrecord.db"

def ensure_logs_folder():
    LOGS_FOLDER.mkdir(exist_ok=True)
    (LOGS_FOLDER / ".keep").touch(exist_ok=True)

def log_debug(message: str):
    ensure_logs_folder()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {message}"
    print(line)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def clear_pycache():
    count = 0
    for root, dirs, _ in os.walk(BASE_DIR):
        for d in dirs:
            if d == "__pycache__":
                path = Path(root) / d
                try:
                    shutil.rmtree(path)
                    log_debug(f"Removed __pycache__: {path}")
                    count += 1
                except Exception as e:
                    log_debug(f"Failed to remove {path}: {e}")
    log_debug(f"Cleared {count} __pycache__ folder(s)")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)
    DATABASE.parent.mkdir(exist_ok=True)

def wait_for_db_ready():
    log_debug("[startup] Waiting for DB to become available (handles lock from previous run)")
    db_ready = False
    for attempt in range(10):
        try:
            with sqlite3.connect(DATABASE, timeout=5) as conn:
                conn.execute("SELECT 1")
            db_ready = True
            break
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                log_debug(f"[startup] DB locked, retrying in 1s ({attempt+1}/10)...")
                time.sleep(1)
            else:
                log_debug(f"[startup] DB error (non-lock): {e}")
                raise
    if not db_ready:
        log_debug("[startup] CRITICAL: Could not access database after 10 retries. Exiting.")
        sys.exit(1)

async def main_loop():
    log_debug("[core] Main asyncio loop running - background tasks active")

    # Run plugin auto-init AFTER the loop has started
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)

    while True:
        await asyncio.sleep(60)

def discover_plugin_names():
    plugins = []
    for path in PLUGIN_FOLDER.glob("*.py"):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        plugins.append(path.stem)
    return plugins

async def auto_run_plugins_async(plugins):
    for plugin_name in plugins:
        try:
            module = __import__(f"Plugin_Files.{plugin_name}", fromlist=["initialize"])
            if hasattr(module, "initialize"):
                module.initialize()
                log_debug(f"[plugins] Auto-initialized {plugin_name}")
            else:
                log_debug(f"[plugins] {plugin_name} has no initialize()")
        except Exception as e:
            log_debug(f"[plugins] Failed to init {plugin_name}: {e}")

def initialize_system():
    ensure_logs_folder()
    ensure_data_folder()
    clear_pycache()
    
    # No backup for sqlite or anything else
    log_debug("RootRecord initialization complete (MySQL mode)")

if __name__ == "__main__":
    initialize_system()
    log_debug("RootRecord is running. Press Ctrl+C to stop.\n")

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("\nShutting down RootRecord...")
        sys.exit(0)