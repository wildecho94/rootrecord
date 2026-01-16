# RootRecord core.py
# Version: 1.43.20260116 – Updated for lowercase 'utils' folder + NSSM/MySQL Workbench instructions

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
import asyncio
import time
import threading

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

def backup_folder(source: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest / f"backup_{timestamp}.zip"
    log_debug(f"Starting backup → {backup_path}")
    # Simple zip backup (skips .db-shm, .db-wal, .zip)
    try:
        shutil.make_archive(str(backup_path.with_suffix('')), 'zip', source)
        log_debug("Backup complete.")
    except Exception as e:
        log_debug(f"Backup failed: {e}")

def backup_system():
    backup_folder(UTILS_FOLDER, BASE_DIR / "backups")
    backup_folder(PLUGIN_FOLDER, BASE_DIR / "backups")
    backup_folder(DATA_FOLDER, BASE_DIR / "backups")

def discover_plugin_names():
    plugins = []
    for file in PLUGIN_FOLDER.glob("*.py"):
        if file.stem == "__init__" or file.stem.startswith('_'):
            continue
        plugins.append(file.stem)
    return sorted(plugins)

def print_discovery_report(plugins):
    print(f"\nDiscovered {len(plugins)} potential plugin(s):")
    print("─" * 60)
    for p in plugins:
        print(f"{p} → main")
    print("─" * 60)

def auto_run_plugins(plugins):
    loop = asyncio.get_event_loop()
    for name in plugins:
        file_path = PLUGIN_FOLDER / f"{name}.py"
        spec = importlib.util.spec_from_file_location(name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        try:
            if hasattr(module, "initialize"):
                coro = module.initialize()
                if asyncio.iscoroutine(coro):
                    asyncio.run_coroutine_threadsafe(coro, loop)
                log_debug(f"→ {name} initialized")
            else:
                log_debug(f"→ {name} loaded (no initialize() function)")
        except Exception as e:
            log_debug(f"Failed to auto-run {name}: {e}")

def initialize_system():
    log_debug("rootrecord system starting...")
    clear_pycache()
    backup_system()
    ensure_data_folder()
    wait_for_db_ready()

    plugins = discover_plugin_names()
    print_discovery_report(plugins)

    auto_run_plugins(plugins)

    # Print MySQL Workbench download link for easy viewing of the DB
    print("\nTo view your MySQL database (rootrecord on localhost:3306):")
    print("Download MySQL Workbench here: https://dev.mysql.com/downloads/workbench/")
    print("Install over CRD, then create connection:")
    print("  - Hostname: localhost")
    print("  - Port: 3306")
    print("  - Username: root")
    print("  - Password: rootrecord123 (or what you set)")
    print("  - Default Schema: rootrecord")
    print("Test Connection → Connect → browse tables like finance_records.\n")

    log_debug(f"\nStartup complete. Found {len(plugins)} potential plugin(s).\n")

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
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    initialize_system()
    log_debug("RootRecord is running. Press Ctrl+C to stop.\n")

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("\nShutting down RootRecord...")
        sys.exit(0)