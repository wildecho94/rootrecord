# RootRecord core.py
# Version: 1.44.20260118 – stripped, no backup, no git touch, just starts plugins + polling

from pathlib import Path
import sys
import asyncio

from utils.db_mysql import engine, init_mysql

BASE_DIR = Path(__file__).parent
PLUGIN_FOLDER = BASE_DIR / "Plugin_Files"
DATA_FOLDER = BASE_DIR / "data"

def ensure_data_folder():
    DATA_FOLDER.mkdir(exist_ok=True)

def discover_plugin_names():
    return [p.stem for p in PLUGIN_FOLDER.glob("*.py") if not p.name.startswith("_") and p.name != "__init__.py"]

async def auto_run_plugins_async(plugins):
    for name in plugins:
        try:
            mod = __import__(f"Plugin_Files.{name}", fromlist=["initialize"])
            if hasattr(mod, "initialize"):
                mod.initialize()
        except:
            pass

async def wait_for_db_ready():
    for attempt in range(15):
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            return
        except:
            await asyncio.sleep(2)
    sys.exit(1)

async def main_loop():
    ensure_data_folder()
    await wait_for_db_ready()
    await init_mysql()
    plugins = discover_plugin_names()
    await auto_run_plugins_async(plugins)
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        sys.exit(1)