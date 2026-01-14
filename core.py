# RootRecord core.py
# Edited Version: 1.42.20260114

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # Add project root to import path

import shutil
import os
from datetime import datetime
import sqlite3
import importlib.util
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
BACKUPS_FOLDER = BASE_DIR / "backups"

def log_debug(message):
    now = datetime.now()
    timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    full_message = f"{timestamp} {message}"
    print(full_message)

    LOGS_FOLDER.mkdir(exist_ok=True)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

def clear_pycache_folders():
    cleared = 0
    for folder in FOLDERS.values():
        pycache = folder / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache)
            log_debug(f"Removed __pycache__: {pycache}")
            cleared += 1
    log_debug(f"Cleared {cleared} __pycache__ folder(s)")

def backup_system():
    now = datetime.now()
    backup_name = f"startup_{now.strftime('%Y%m%d_%H%M%S')}"
    backup_dir = BACKUPS_FOLDER / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    log_debug(f"Starting backup → {backup_dir}")

    for name, folder in FOLDERS.items():
        if folder.exists():
            dest = backup_dir / name
            shutil.copytree(folder, dest, ignore=shutil.ignore_patterns("*.zip"))
            log_debug(f"Backed up {name} (skipped .zip files)")

    data_dest = backup_dir / "data"
    shutil.copytree(DATA_FOLDER, data_dest, ignore=shutil.ignore_patterns("*.zip"))
    log_debug(f"Backed up data folder (database + skipped .zip)")

    log_debug("Backup completed")

def prepare_folders():
    for name, folder in FOLDERS.items():
        if not folder.exists():
            folder.mkdir(parents=True)
            log_debug(f"Created {name} folder")
        else:
            log_debug(f"✓ {name.capitalize()}_Files")

def discover_plugins():
    plugins = {}
    log_debug("\nDiscovered potential plugin(s):")

    # Search ALL .py files in the entire project root and subfolders
    for path in BASE_DIR.rglob("*.py"):
        # Skip internal files and known non-plugin locations
        if (
            path.name.startswith("__") or
            path.name == "__init__.py" or
            "Core_Files" in path.parts or
            "Handler_Files" in path.parts or
            "__pycache__" in path.parts or
            "logs" in path.parts or
            "backups" in path.parts or
            "data" in path.parts
        ):
            continue

        name = path.stem
        try:
            # Use relative module name
            rel_path = path.relative_to(BASE_DIR)
            module_name = ".".join(rel_path.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Only load as plugin if it has initialize()
            if hasattr(module, "initialize"):
                plugins[name] = module
                log_debug(f"{name} → initialize() found (path: {path})")
            else:
                log_debug(f"{name} → skipped (no initialize())")
        except Exception as e:
            log_debug(f"Failed to load {path.name}: {e}")

    log_debug(f"────────────────────────────────────────────────────────────\n")
    log_debug(f"Total plugins loaded: {len(plugins)}\n")

    return plugins

def auto_run_plugins(plugins):
    for name, module in plugins.items():
        try:
            if hasattr(module, "initialize"):
                module.initialize()
            log_debug(f"→ {name} initialized")
        except Exception as e:
            log_debug(f"Failed to auto-run {name}: {e}")

def initialize_system():
    os.system('cls' if os.name == 'nt' else 'clear')
    now = datetime.now()
    log_debug(f"rootrecord system starting at {now.isoformat()}...")

    clear_pycache_folders()
    backup_system()
    prepare_folders()

    plugins = discover_plugins()
    auto_run_plugins(plugins)

    log_debug(f"\nStartup complete. Found {len(plugins)} potential plugin(s).\n")

async def main_loop():
    log_debug("[core] Main asyncio loop running - all background tasks active")
    while True:
        await asyncio.sleep(60)  # Keep loop alive

if __name__ == "__main__":
    initialize_system()
    log_debug("RootRecord is running. Press Ctrl+C to stop.\n")

    # Start Cloudflare Tunnel
    try:
        from plugins.web.tunnel import initialize as tunnel_init
        tunnel_init()
        log_debug("[core] Cloudflare Tunnel initialized and started")
    except ImportError as e:
        log_debug(f"[core] Failed to import tunnel.py: {e}")
    except Exception as e:
        log_debug(f"[core] Tunnel startup error: {e}")

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log_debug("\nShutting down RootRecord...")
        sys.exit(0)