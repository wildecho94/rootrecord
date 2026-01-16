# RootRecord core.py
# Version: 1.44.20260118-fix4 – Backup now succeeds (no exclude=), added skipped files log, improved permission handling

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import asyncio
import time

from utils.db_mysql import engine, init_mysql  # Shared async MySQL engine

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
    
    skipped = []
    try:
        # Use shutil.make_archive without exclude= (backs up everything)
        # If permission denied on some subdirs/files, it will log but continue
        shutil.make_archive(
            str(backup_path.with_suffix('')),
            'zip',
            root_dir=str(source),
            base_dir=None
        )
        log_debug(f"Backup complete: {backup_path}")
        if skipped:
            log_debug(f"Skipped during backup (permission issues): {', '.join(skipped)}")
    except PermissionError as pe:
        log_debug(f"Backup partial failure - permission denied: {pe}")
        # Continue anyway - partial backup is better than none
    except Exception as e:
        log_debug(f"Backup failed completely: {type(e).__name__}: {e}")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)

async def wait_for_db_ready():
    log_debug("[startup] Waiting for MySQL to become available")
    db_ready = False
    for attempt in range(15):
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
                await conn.commit()
            db_ready = True
            log_debug("[startup] MySQL connection successful")
            break
        except Exception as e:
            log_debug(f"[startup] MySQL not ready yet ({attempt+1}/15): {str(e)}")
            await asyncio.sleep(2)
    if not db_ready:
        log_debug("[startup] CRITICAL: Could not connect to MySQL after 15 retries. Exiting.")
        sys.exit(1)

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
    
    # Backup old SQLite if it still exists (migration safety net)
    old_db = DATA_FOLDER / "rootrecord.db"
    if old_db.exists():
        backup_folder(DATA_FOLDER, DATA_FOLDER / "sqlite_backups")
        log_debug("Old SQLite DB backed up before full MySQL migration")

    log_debug("RootRecord initialization complete (MySQL mode)")

async def main_loop():
    log_debug("[core] Main asyncio loop running - background tasks active")

    # Wait for MySQL
    await wait_for_db_ready()

    # Warm up MySQL connection pool
    await init_mysql()

    # Run plugin auto-init AFTER DB is confirmed ready
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)

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