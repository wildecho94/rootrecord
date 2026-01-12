# RootRecord

**Modular Python plugin system with auto-maintained templates**

**Version:** 20260112 ("Merged & Visible")  
**Last edited:** January 12, 2026  
**Status:** Early / active development

RootRecord is a lightweight, self-bootstrapping framework for building extensible Python applications — especially bots and automation tools — using a clean, plugin-based architecture.

### Current Features

**Automatic setup & safety**  
- Creates `Core_Files/`, `Handler_Files/`, `Plugin_Files/` folders (with `__init__.py`)  
- Generates blank plugin templates when needed  
- Clears `__pycache__` on startup  
- Creates timestamped backups (skips `.zip` files)  
- Mirrors all console output → `debug_rootrecord.log`  

**Plugin system**  
- Auto-discovers `Plugin_Files/*.py` files (especially `*_plugin.py`)  
- Supports single-file plugins or split (main/core/handler)  
- Calls `initialize()` hook if defined  

**Telegram bot + GPS tracking** (single merged plugin: `telegram_plugin.py`)  
- Loads token from `config_telegram.json` (**never commit this file!**)  
- Auto-adds `/start` command  
- Loads additional commands dynamically from `commands/` folder  
- Saves **every** location pin and **every live location update/edit** to database immediately  
- Full verbose console logging of all messages, commands, locations, callbacks, saves  
- Background polling with `drop_pending_updates=True`  

**Uptime tracking** (single-file example)  
- Tracks start/stop/crash events  
- Calculates uptime percentage  
- Prints stats every 60 seconds + on startup  
- Saves snapshots to `uptime_stats` table  

**Centralized task scheduler** (`Core_Files/scheduler.py`)  
- Reliable periodic jobs without starvation (e.g. uptime stats)  

**GitHub auto-publish** (`publish_rootrecord.py`)  
- Commits & pushes changes automatically on startup  
- Handles deleted/moved files (`git add -u`)  
- **Security warning:** Contains GitHub token — **delete after use!**  

### Architecture Highlights (Jan 12, 2026)

- Telegram bot + GPS location saving merged into **one file** (`telegram_plugin.py`) → no more load-order races or late registration  
- Immediate DB writes for every location update (regular pins + live shares + edits)  
- Verbose console output for every step, update, and save action  
- Redundant files removed (old GPS handler/core, separate Telegram handler)  
- Commands still loaded dynamically from `commands/` folder  
- Scheduler and uptime plugin continue to run independently  

### Changelog – 20260112 ("Merged & Visible")

- **Merged** Telegram bot + GPS tracking into single `telegram_plugin.py` (no more separate plugins or races)  
- **Immediate saves** for every location pin, live share, and live edit  
- **Verbose logging** — every message/command/location/callback/save printed in console  
- Removed redundant files: `a_gps_plugin.py`, `gps_tracker_handler.py`, `gps_tracker_core.py`, `telegram_handler.py`  
- Fixed live location edits (now explicitly handled via `EDITED_MESSAGE & filters.LOCATION`)  
- Cleaned up print overrides and color attempts (stable plain-text output)  

### Security Notes

- **Never commit** `config_telegram.json` or any tokens/secrets  
- `publish_rootrecord.py` contains GitHub PAT → **delete after use**  
- Regenerate Telegram bot token if ever exposed  
- Add `.gitignore` entries for secrets, logs, backups, `__pycache__`  

### Roadmap (2026)

**Short-term**  
- Stabilize Telegram/GPS saves & logging  
- Crash detection & graceful shutdown  
- Expose scheduler to plugins for custom periodic tasks  

**Medium-term**  
- Plugin hot-reload  
- Advanced command parsing (args, prefixes)  
- User/session tracking in DB  
- Multi-platform exploration (Discord?)  

**Long-term**  
- Self-healing framework  
- Plugin marketplace  
- AI agent hooks  

### Contributing

Early-stage project — breaking changes still possible.  
Current focus: **stability & visibility > new features**

Open issues/PRs welcome — especially bug fixes, plugin ideas, logging improvements.

---
**Live repo:** https://github.com/wildecho94/rootrecord  
**Bot:** @RootRecordCore_bot (send /start & locations)  
**DB:** `data/rootrecord.db` → `gps_records` table (fills on every location update)  

**RootRecord** — bootstrapping your ideas, one plugin at a time.