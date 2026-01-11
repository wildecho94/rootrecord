# RootRecord core.py
# Edited Version: 1.42.20260111

from pathlib import Path
import sys
import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
import time
import asyncio

BASE_DIR = Path(__file__).parent

CORE_FOLDER    = BASE_DIR / "Core_Files"
HANDLER_FOLDER = BASE_DIR / "Handler_Files"
PLUGIN_FOLDER  = BASE_DIR / "Plugin_Files"

FOLDERS = {
    "core":    CORE_FOLDER,
    "handler": HANDLER_FOLDER,
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
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

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
        print(f"  Cleared {count} __pycache__ folder(s)")

def ignore_zip_files(src, names):
    return [name for name in names if name.lower().endswith('.zip')]

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
                ignore=ignore_zip_files,
                dirs_exist_ok=True
            )
            log_debug(f"  Backed up {name} (skipped .zip files)")

    if DATA_FOLDER.exists():
        shutil.copytree(
            DATA_FOLDER, backup_dir / "data",
            ignore=ignore_zip_files,
            dirs_exist_ok=True
        )
        log_debug("  Backed up data folder (database + skipped .zip)")

    log_debug("Backup completed")

def ensure_folder_and_init(folder: Path):
    folder.mkdir(exist_ok=True)
    init = folder / "__init__.py"
    if not init.exists():
        init.touch()
        print(f"  Created __init__.py in {folder.name}")

def ensure_all_folders():
    print("Preparing folders...")
    for folder in FOLDERS.values():
        ensure_folder_and_init(folder)
        print(f"  ✓ {folder.name}")

def ensure_database():
    DATA_FOLDER.mkdir(exist_ok=True)
    if DATABASE.exists():
        return

    print("  → Creating initial database: rootrecord.db")
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_info (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("INSERT OR REPLACE INTO system_info (key,value) VALUES ('version','0.1-initial')")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  Database creation failed: {e}")

def ensure_blank_plugin_template():
    name = "blank_plugin"
    files = [
        (PLUGIN_FOLDER / f"{name}.py",        "main entry point"),
        (CORE_FOLDER   / f"{name}_core.py",   "core logic"),
        (HANDLER_FOLDER/ f"{name}_handler.py","event/command handlers")
    ]

    missing = [p for p, _ in files if not p.exists()]
    if not missing:
        return

    print(f"  → Missing blank_plugin files: {len(missing)}")
    for path, purpose in files:
        if path.exists():
            continue

        content = f'''# {path.name}
"""
blank_plugin - {purpose}
Auto-maintained template
"""

print("[blank_plugin] {path.stem} loaded")

# === Your code goes here ===

'''
        try:
            path.write_text(content.strip(), encoding="utf-8")
            print(f"    Created: {path.name}")
        except Exception as e:
            print(f"    Failed to create {path.name}: {e}")

def discover_plugin_names() -> set:
    names = set()
    for path in PLUGIN_FOLDER.glob("*.py"):
        stem = path.stem
        if stem == "__init__":
            continue
        if stem.endswith("_core") or stem.endswith("_handler"):
            continue
        names.add(stem)
    return names

def get_plugin_status(name: str) -> list:
    parts = []
    if (PLUGIN_FOLDER / f"{name}.py").is_file():
        parts.append("main")
    if (CORE_FOLDER / f"{name}_core.py").is_file():
        parts.append("core")
    if (HANDLER_FOLDER / f"{name}_handler.py").is_file():
        parts.append("handler")
    return parts

def print_discovery_report(plugins: set):
    if not plugins:
        print("\nNo plugins detected in Plugin_Files/")
        return

    print(f"\nDiscovered {len(plugins)} potential plugin(s):")
    print("─" * 60)
    for name in sorted(plugins):
        parts = get_plugin_status(name)
        status = ", ".join(parts) if parts else "incomplete"
        print(f"  {name:18} → {status}")
    print("─" * 60)

def auto_run_plugins(plugins: set):
    print("\nAuto-running discovered plugins...")
    for name in sorted(plugins):
        plugin_path = PLUGIN_FOLDER / f"{name}.py"
        if not plugin_path.exists():
            continue

        try:
            spec = importlib.util.spec_from_file_location(name, str(plugin_path))
            if not spec or not spec.loader:
                print(f"  Failed to load {name}: invalid module")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "initialize"):
                module.initialize()
                print(f"  → {name} initialized")
            else:
                print(f"  → {name} loaded (no initialize() function)")

        except Exception as e:
            print(f"  Failed to auto-run {name}: {e}")

def initialize_system():
    print("rootrecord system starting...\n")

    clear_pycache()
    make_startup_backup()
    ensure_all_folders()

    ensure_database()
    ensure_blank_plugin_template()

    plugins = discover_plugin_names()
    print_discovery_report(plugins)

    auto_run_plugins(plugins)

    print(f"\nStartup complete. Found {len(plugins)} potential plugin(s).\n")

async def main_loop():
    while True:
        await asyncio.sleep(60)  # Keep event loop alive, allow tasks to run

if __name__ == "__main__":
    initialize_system()
    print("RootRecord is running. Press Ctrl+C to stop.\n")

    # Start main asyncio loop for background tasks
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nShutting down RootRecord...")
        sys.exit(0)