# RootRecord v1.42.20260111

**First official release**  
Modular Python plugin system with auto-maintained templates and Telegram integration

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

- **Telegram plugin** (working version)
  - Loads from `Plugin_Files/telegram_plugin.py`
  - Uses `config_telegram.json` for bot token
  - Dynamic command loading from `commands/` folder
  - Auto-creates `/start` command if missing
  - Real-time terminal logging of all incoming messages/commands
  - Background polling via daemon thread

- **Uptime plugin** (reliable tracking)
  - Tracks total uptime/downtime from raw DB events (start/stop/crash)
  - Prints yellow stats to console every 60 seconds + on startup
  - Saves snapshots to `uptime_stats` table (timestamp, up/down sec, percentage)
  - Uses separate daemon thread for consistent timing

- **GitHub publishing script** (`publish_rootrecord.py`)
  - Auto-commits & pushes changes on every startup
  - Includes recent log excerpt

- **Debug logging**
  - All console output mirrored to `debug_rootrecord.log`

## Changelog (v1.42.20260111 - First Release)

- Stabilized plugin loading & discovery
- Telegram bot fully functional with /start command and real-time message logging
- Added reliable uptime tracking with daemon thread (no asyncio starvation)
- All console output now mirrored to debug_rootrecord.log
- Improved backup system (skips .zip, logs every step)
- Cleaned sensitive files from history (config_telegram.json removed)

## Project Structure
