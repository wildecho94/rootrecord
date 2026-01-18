# RootRecord core.py
# Version: 1.42.20260118 – Paths updated for new root I:\RootRecord
#         MySQL data dir is now I:\MYSQL (set in my.ini if needed)

from pathlib import Path
import sys
import os
from datetime import datetime
import importlib.util
import asyncio
import shutil

from utils.db_mysql import engine
from sqlalchemy import text

BASE_DIR = Path(__file__).parent

# Logs and data in writable sibling folders
LOGS_FOLDER = BASE_DIR / "logs"
DATA_FOLDER = BASE_DIR / "data"

DEBUG_LOG = LOGS_FOLDER / "debug_rootrecord.log"

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
    if count > 0:
        log_debug(f"Cleared {count} __pycache__ folders")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)
    (DATA_FOLDER / ".keep").touch(exist_ok=True)

async def ensure_all_tables():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE DATABASE IF NOT EXISTS rootrecord"))
        await conn.execute(text("USE rootrecord"))
        # Uptime tables - exact schema to match your insert (VARCHAR(50) for status to avoid truncation)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS uptime_records (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                timestamp DATETIME NOT NULL,
                INDEX idx_timestamp (timestamp)
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS uptime_stats (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                uptime_pct FLOAT NOT NULL,
                total_up VARCHAR(50) NOT NULL,
                total_down VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                snapshot_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_snapshot_time (snapshot_time)
            )
        """))

def discover_plugin_names():
    plugins = []
    for path in (BASE_DIR / "Plugin_Files").glob("*.py"):
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

async def main_loop():
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)

    from Plugin_Files.telegram_plugin import bot_main, shutdown_bot
    bot_task = asyncio.create_task(bot_main())

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        log_debug("[core] Main loop cancelled")
    finally:
        await shutdown_bot()
        bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)

async def initialize_system():
    await ensure_all_tables()
    ensure_logs_folder()
    ensure_data_folder()
    clear_pycache()
    log_debug("RootRecord initialization complete (MySQL mode)")

if __name__ == "__main__":
    asyncio.run(initialize_system())
    log_debug("RootRecord is running. Press Ctrl+C to stop.\n")

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("\nShutting down RootRecord...")
    sys.exit(0)