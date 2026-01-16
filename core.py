# RootRecord core.py
# Version: 1.44.20260118-fix5 – Skip large/old SQLite backups to prevent Git LFS rejection

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import asyncio
import time

from utils.db_mysql import engine, init_mysql

BASE_DIR = Path(__file__).parent

UTILS_FOLDER   = BASE_DIR / "utils"
PLUGIN_FOLDER  = BASE_DIR / "Plugin_Files"

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
    print(line, flush=True)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()

def clear_pycache():
    log_debug("Starting pycache clear...")
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

    # Skip backup if source contains large SQLite DB (prevents Git push failure)
    old_db = source / "rootrecord.db"
    if old_db.exists() and old_db.stat().st_size > 100 * 1024 * 1024:  # >100 MB
        log_debug(f"SKIPPING backup: old SQLite DB too large ({old_db.stat().st_size / (1024*1024):.2f} MB) – would break Git push")
        log_debug("Migration complete: delete data/rootrecord.db manually when ready")
        return

    try:
        shutil.make_archive(str(backup_path.with_suffix('')), 'zip', str(source))
        log_debug(f"Backup complete: {backup_path}")
    except PermissionError as pe:
        log_debug(f"Backup skipped - permission issue: {pe}")
    except Exception as e:
        log_debug(f"Backup failed: {type(e).__name__}: {e}")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)
    log_debug("Data folder ensured")

async def wait_for_db_ready():
    log_debug("[startup] Waiting for MySQL...")
    db_ready = False
    for attempt in range(15):
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
                await conn.commit()
            db_ready = True
            log_debug("[startup] MySQL OK")
            break
        except Exception as e:
            log_debug(f"MySQL attempt {attempt+1