# RootRecord core.py
# Version: 1.42.20260117 – Integrated asyncio loop for Telegram bot + clean shutdown
# Changes for current fixes:
#   - Plugins auto-discovered and initialized in main loop
#   - Telegram bot runs in main asyncio loop (no separate Thread)
#   - Awaits bot_main() and handles shutdown with engine.dispose()
#   - Added ready message after plugin init for easier debugging

from pathlib import Path
import sys
import os
from datetime import datetime
import shutil
import asyncio

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
    else:
        log_debug("No __pycache__ folders found")

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)
    (DATA_FOLDER / ".keep").touch(exist_ok=True)

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
                log_debug(f"[plugins] {plugin_name} has no initialize() function")
        except Exception as e:
            log_debug(f"[plugins] Failed to init {plugin_name}: {e}")

async def main_loop():
    # Discover and initialize all plugins now that asyncio loop is running
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)

    # Import and start Telegram bot in the main loop
    from Plugin_Files.telegram_plugin import bot_main, shutdown_bot
    bot_task = asyncio.create_task(bot_main())

    try:
        # Main idle loop – keeps the program alive
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        log_debug("[core] Main loop cancelled during shutdown")
    finally:
        # Clean shutdown: stop bot and dispose DB connections
        await shutdown_bot()
        if bot_task:
            bot_task.cancel()
            await asyncio.gather(bot_task, return_exceptions=True)

def initialize_system():
    ensure_logs_folder()
    ensure_data_folder()
    clear_pycache()
    
    # No backups – completely removed as per project direction
    
    log_debug("RootRecord initialization complete (MySQL mode)")
    print("[core] All plugins initialized – system ready. Send locations/commands to test.")

if __name__ == "__main__":
    initialize_system()
    log_debug("RootRecord is running. Press Ctrl+C to stop.\n")

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("\nShutting down RootRecord...")
    except Exception as e:
        log_debug(f"[core] Unexpected crash in main: {e}")
    finally:
        sys.exit(0)