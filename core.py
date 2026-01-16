# RootRecord core.py
# Version: 1.44.20260118-fix6 – Prevent recursive backup of old .zip files, skip large DB

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
    log_debug("Clearing pycache...")
    count = 0
    for root, dirs, _ in os.walk(BASE_DIR):
        for d in dirs:
            if d == "__pycache__":
                path = Path(root) / d
                try:
                    shutil.rmtree(path)
                    log_debug(f"Removed: {path}")
                    count += 1
                except Exception as e:
                    log_debug(f"Skip {path}: {e}")
    log_debug(f"Cleared {count} pycache folders")

def backup_folder(source: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest / f"backup_{timestamp}.zip"
    log_debug(f"Backup start → {backup_path}")

    # Safety: skip if old DB is huge
    old_db = source / "rootrecord.db"
    if old_db.exists() and old_db.stat().st_size > 100 * 1024 * 1024:
        log_debug(f"SKIP backup: rootrecord.db too big ({old_db.stat().st_size / (1024**2):.1f} MB)")
        return

    skipped = []
    try:
        # Use zipfile for fine control: exclude any .zip in source (no recursive backups)
        import zipfile
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source):
                for file in files:
                    full_path = Path(root) / file
                    if full_path.suffix.lower() == '.zip':
                        skipped.append(str(full_path))
                        continue  # skip old backups
                    arcname = str(full_path.relative_to(source))
                    try:
                        zf.write(full_path, arcname)
                    except PermissionError:
                        skipped.append(f"{full_path} (locked)")
                    except Exception as e:
                        log_debug(f"Skip {full_path}: {e}")
        log_debug(f"Backup complete: {backup_path}")
        if skipped:
            log_debug(f"Skipped {len(skipped)} files: {', '.join(skipped[:5])}{'...' if len(skipped)>5 else ''}")
    except Exception as e:
        log_debug(f"Backup failed: {type(e).__name__}: {e}")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)

async def wait_for_db_ready():
    log_debug("[startup] MySQL wait...")
    for attempt in range(15):
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            log_debug("[startup] MySQL connected")
            return
        except Exception as e:
            log_debug(f"Attempt {attempt+1}/15: {str(e)}")
            await asyncio.sleep(2)
    log_debug("CRITICAL: MySQL failed")
    sys.exit(1)

def discover_plugin_names():
    return [p.stem for p in PLUGIN_FOLDER.glob("*.py") if not p.name.startswith("_") and p.name != "__init__.py"]

async def auto_run_plugins_async(plugins):
    log_debug(f"Loading {len(plugins)} plugins...")
    for name in plugins:
        try:
            mod = __import__(f"Plugin_Files.{name}", fromlist=["initialize"])
            if hasattr(mod, "initialize"):
                mod.initialize()
                log_debug(f"  + {name}")
            else:
                log_debug(f"  - {name} (no init)")
        except Exception as e:
            log_debug(f"  ERROR {name}: {e}")

def initialize_system():
    log_debug("Init start")
    ensure_logs_folder()
    ensure_data_folder()
    clear_pycache()
    
    old_db = DATA_FOLDER / "rootrecord.db"
    if old_db.exists():
        log_debug("Old DB found – backup attempt")
        backup_folder(DATA_FOLDER, DATA_FOLDER / "sqlite_backups")
    
    log_debug("Init done (MySQL)")

async def main_loop():
    log_debug("Main loop")
    await wait_for_db_ready()
    await init_mysql()
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)
    
    print("\n" + "═"*60)
    print("ROOTRECORD LIVE – Bot polling active")
    print("Send /start or location to test")
    print("Ctrl+C here to stop")
    print("═"*60 + "\n", flush=True)
    
    counter = 0
    while True:
        counter += 1
        if counter % 30 == 0:  # every 30 min
            log_debug(f"[alive] {datetime.now().strftime('%H:%M:%S')} – cycle {counter}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        initialize_system()
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("Shutdown (Ctrl+C)")
    except Exception as e:
        log_debug(f"FATAL CRASH: {e}\n{traceback.format_exc()}")
        sys.exit(1)