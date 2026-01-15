# RootRecord core.py
# Version: 1.43.20260117 – Skip locked SQLite temp files + retry on DB lock at startup

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
import asyncio
import time

BASE_DIR = Path(__file__).parent

CORE_FOLDER    = BASE_DIR / "Core_Files"
PLUGIN_FOLDER  = BASE_DIR / "Plugin_Files"

FOLDERS = {
    "core":    CORE_FOLDER,
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
    if count:
        log_debug(f"  Cleared {count} __pycache__ folder(s)")

def ignore_temp_db_files(src, names):
    """Ignore temporary SQLite files (.db-shm, .db-wal) and .zip"""
    return [
        name for name in names
        if name.lower().endswith(('.zip', '.db-shm', '.db-wal'))
    ]

def make_startup_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BASE_DIR / "backups" / f"startup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    log_debug(f"Starting backup → {backup_dir}")

    for name, source in FOLDERS.items():
        if source.exists():
            dest = backup_dir / name
            shutil.copytree(
                source, dest,
                ignore=ignore_temp_db_files,
                dirs_exist_ok=True
            )
            log_debug(f"  Backed up {name} (skipped temp DB files & .zip)")

    if DATA_FOLDER.exists():
        shutil.copytree(
            DATA_FOLDER, backup_dir / "data",
            ignore=ignore_temp_db_files,
            dirs_exist_ok=True
        )
        log_debug("  Backed up data folder (skipped temp DB files & .zip)")

    log_debug("Backup complete.")

def ensure_all_folders():
    for folder in FOLDERS.values():
        folder.mkdir(exist_ok=True)

def ensure_database():
    DATA_FOLDER.mkdir(exist_ok=True)
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS _system_marker (dummy INTEGER)")
        conn.commit()
    log_debug("Database folder and root file ensured.")

def ensure_blank_plugin_template():
    blank = PLUGIN_FOLDER / "blank_plugin.py"
    if not blank.exists():
        with open(blank, "w", encoding="utf-8") as f:
            f.write('''# blank_plugin.py
"""
blank_plugin - main entry point
Auto-maintained template
"""

print("[blank_plugin] blank_plugin loaded")

# === Your code goes here ===
''')
        log_debug("Created blank_plugin.py template")

def discover_plugin_names():
    if not PLUGIN_FOLDER.exists():
        return set()
    return {p.stem for p in PLUGIN_FOLDER.glob("*.py") if not p.stem.startswith("_")}

def print_discovery_report(plugins: set):
    if not plugins:
        log_debug("\nNo plugins detected in Plugin_Files/")
        return

    log_debug(f"\nDiscovered {len(plugins)} potential plugin(s):")
    log_debug("─" * 60)
    for name in sorted(plugins):
        status = "main"
        if (CORE_FOLDER / f"{name}_core.py").is_file():
            status += ", core"
        log_debug(f"  {name:18} → {status}")
    log_debug("─" * 60)

def auto_run_plugins(plugins: set):
    log_debug("\nAuto-running discovered plugins...")
    for name in sorted(plugins):
        plugin_path = PLUGIN_FOLDER / f"{name}.py"
        if not plugin_path.exists():
            continue

        try:
            spec = importlib.util.spec_from_file_location(name, str(plugin_path))
            if not spec or not spec.loader:
                log_debug(f"  Failed to load {name}: invalid module")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "initialize"):
                module.initialize()
                log_debug(f"  → {name} initialized")
            else:
                log_debug(f"  → {name} loaded (no initialize() function)")

        except Exception as e:
            log_debug(f"  Failed to auto-run {name}: {e}")

def initialize_system():
    log_debug("rootrecord system starting...\n")

    clear_pycache()
    make_startup_backup()
    ensure_all_folders()

    ensure_database()
    ensure_blank_plugin_template()

    # Wait for DB to become available (handles lock from previous run)
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

    plugins = discover_plugin_names()
    print_discovery_report(plugins)

    auto_run_plugins(plugins)

    log_debug(f"\nStartup complete. Found {len(plugins)} potential plugin(s).\n")

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