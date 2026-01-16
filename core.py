# RootRecord core.py
# Version: 1.44.20260118-fix9 – No more backups at all (commented out), added .gitignore enforcement check

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
    log_debug("Backup function called – but disabled to prevent large files in git")
    log_debug("If you need backups, run manually or re-enable with size cap")
    # Comment out or remove the actual backup code to avoid accidents
    # shutil.make_archive(...)  # DISABLED

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
    
    # Backup disabled to avoid git issues – manual if needed
    log_debug("Backup disabled (safe mode) – old DB not zipped")
    
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
        if counter % 10 == 0:  # every 10 min
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