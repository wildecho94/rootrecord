# RootRecord core.py
# Version: 1.44.20260118-fix12 – Backup disabled, git remote forced to HTTPS in startup

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import asyncio
import time
import traceback
import subprocess

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
    log_debug("Backup function called – still disabled to prevent any git issues")
    log_debug("Manual backup if needed: copy data/ folder elsewhere")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)
    log_debug("Data folder ensured")

def fix_git_remote():
    log_debug("Checking/fixing git remote URL to HTTPS (fixes publickey error)")
    try:
        result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
        if "git@github.com" in result.stdout:
            log_debug("SSH remote detected – switching to HTTPS")
            subprocess.run("git remote set-url origin https://github.com/wildecho94/rootrecord.git", shell=True, check=True)
            log_debug("Git remote set to HTTPS – publish should work now")
        else:
            log_debug("Remote already HTTPS or correct")
    except Exception as e:
        log_debug(f"Failed to fix git remote: {e}")

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
    
    log_debug("Backup disabled (safe mode) – no zip created")
    
    fix_git_remote()  # Force HTTPS remote for publish
    
    log_debug("Init done (MySQL)")

async def main_loop():
    log_debug("Main loop start")
    await wait_for_db_ready()
    await init_mysql()
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)
    
    print("\n" + "═"*70)
    print("ROOTRECORD FULLY LIVE – Bot polling active")
    print("Send /start, /uptime, or location to bot in Telegram")
    print("Console shows [alive] every 10 min + activity")
    print("Ctrl+C here to stop safely")
    print("═"*70 + "\n", flush=True)
    
    counter = 0
    while True:
        counter += 1
        if counter % 10 == 0:
            log_debug(f"[alive] {datetime.now().strftime('%H:%M:%S')} – cycle {counter}")
        await asyncio.sleep(60)

def graceful_shutdown():
    log_debug("Graceful shutdown requested...")
    log_debug("All systems down - safe exit")

if __name__ == "__main__":
    try:
        initialize_system()
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("Shutdown (Ctrl+C)")
        graceful_shutdown()
    except Exception as e:
        log_debug(f"FATAL CRASH: {e}\n{traceback.format_exc()}")
        graceful_shutdown()
        sys.exit(1)
    finally:
        log_debug("=== RootRecord exit ===")