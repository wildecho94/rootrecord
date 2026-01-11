# RootRecord

**Modular Python plugin system with auto-maintained templates**  
Version: v1.42.20260111

RootRecord is a lightweight, extensible framework designed for rapid development of modular Python applications with plugin architecture.

Current status: **very early development / proof-of-concept stage** (January 11, 2026)

## Current Features

- **Plugin system** (auto-discovery & loading)
  - Plugins live in `Plugin_Files/`
  - Recognizes `{plugin_name}.py`, `{plugin_name}_core.py`, `{plugin_name}_handler.py`, `{plugin_name}_main.py`
  - Automatic execution of `initialize()` function if present

- **Folder structure auto-preparation**
  - Creates / checks `Core_Files/`, `Handler_Files/`, `Plugin_Files/`
  - Clears `__pycache__` folders on startup

- **Startup backup system**
  - Creates timestamped backups in `backups/`
  - Skips `.zip` files
  - Backs up core/handler/plugin files + `data/` folder (including database)

- **Telegram plugin** (basic working version)
  - Loads from `Plugin_Files/telegram_plugin.py`
  - Uses `config_telegram.json` for bot token
  - Dynamic command loading from top-level `commands/` folder
  - Auto-creates `start_cmd.py` if missing
  - Real-time terminal logging of all incoming messages/commands (teal color)
  - Background polling via daemon thread

- **GitHub publishing script** (`publish_rootrecord.py`)
  - Auto-commits & pushes changes on every startup
  - Appends recent log excerpt to commit output
  - Safe handling of existing repo

- **Debug logging**
  - All important startup events written to `debug_rootrecord.log`

## Project Structure (as of Jan 2026)
