**RootRecord**

**Modular Python plugin system with auto-maintained templates**

**Version:** 20260112 ("Merged & Visible")  
**Last edited:** January 12, 2026  
**Status:** Early/active development

RootRecord is a lightweight, extensible framework for building modular Python applications — especially bots and automation tools — using a clean plugin-based architecture.

**Status:** Early development / active bootstrapping (January 12, 2026)


### Key Improvements (Jan 12, 2026)

- **Merged Telegram + GPS into single plugin** (`telegram_plugin.py`)  
  - No more load-order races or late registration  
  - Immediate saving of regular & live locations to DB  
  - Full verbose console logging of every update/command/location/callback  

- **Centralized asyncio loop & scheduler** (`scheduler.py`)  
  - Reliable periodic tasks without starvation  

- **Startup safety & visibility**  
  - Clears `__pycache__`  
  - Timestamped backups (skips .zip)  
  - All console output mirrored to `debug_rootrecord.log`  

- **Plugin auto-discovery & loading**  
  - Scans `Plugin_Files/*.py` (especially `*_plugin.py` files)  
  - Supports single-file or split plugins  
  - Calls `initialize()` if defined  

### Current Features

**Automatic setup & safety**  
- Creates `Core_Files/`, `Handler_Files/`, `Plugin_Files/` (with `__init__.py`)  
- Generates blank plugin templates when needed  
- Clears `__pycache__` on startup  
- Makes timestamped backups (skips `.zip` files)  
- Mirrors console to `debug_rootrecord.log`  

**Plugin system**  
- Auto-discovers `Plugin_Files/*.py` files  
- Supports single-file plugins or split (main/core/handler)  
- Calls `initialize()` hook if present  

**Telegram integration** (fully working bot)  
- Loads token from `config_telegram.json` (never commit this file!)  
- Auto-adds `/start` command (and loads others from `commands/`)  
- Saves every location & live location update to DB instantly  
- Real-time verbose logging of all messages, commands, polling, updates  
- Background polling with drop-pending-updates  

**Uptime tracking** (single-file example)  
- Tracks start/stop/crash events  
- Calculates uptime percentage  
- Prints yellow stats every 60 seconds + on startup  
- Saves snapshots to `uptime_stats` table  

**GitHub auto-publish** (`publish_rootrecord.py`)  
- Commits & pushes changes automatically on startup  
- Handles deleted/moved files (`git add -u`)  
- **Security:** Contains GitHub token — delete after use!  

**Centralized task scheduling** (`scheduler.py`)  
- Reliable periodic jobs (e.g. uptime stats)  

### Changelog Highlights

**v1.43.20260112 (Jan 12, 2026)**  
- Merged Telegram + GPS into single `telegram_plugin.py` (no more separate files or races)  
- Immediate DB saves for all locations/live locations/edits  
- Full verbose console logging (every message, location, save)  
- Fixed print override recursion crash  
- Cleaned up redundant files (`gps_tracker_*`, old handlers)  

**v1.42.20260111 (Jan 11, 2026)**  
- Added `Core_Files/scheduler.py` for centralized tasks  
- Console output mirrored to `debug_rootrecord.log`  
- Reliable uptime plugin with DB snapshots  
- Detailed Telegram logging & polling  

**v1.42.20260110**  
- Initial bootstrap: folders, backups, plugin discovery  
- Basic Telegram bot with /start & message logging  
- Uptime plugin with DB state  
- GitHub auto-publish  

### Goals & Roadmap (2026)

**Short-term**  
- Stabilize Telegram/GPS saves & logging  
- Add crash detection & graceful shutdown  
- Expose scheduler to plugins for custom periodic tasks  

**Medium-term**  
- Plugin hot-reload support  
- Advanced command parsing (prefixes, arguments)  
- User/session tracking in DB  
- Multi-platform exploration (Discord?)  

**Long-term vision**  
- Self-healing framework  
- Plugin marketplace  
- AI agent hooks  
- Enterprise logging & monitoring  

### Security Notes

- **Never commit** `config_telegram.json` or any tokens/secrets  
- `publish_rootrecord.py` contains GitHub PAT → **delete after use**  
- Regenerate Telegram bot token immediately if ever exposed  
- Add `.gitignore` entries for secrets, logs, backups  

### Contributing

Early-stage project — breaking changes still likely.  
Current focus: **stability > features**

Feel free to open issues/PRs — especially around plugin ideas, bug fixes, or logging enhancements.

---
**Live repo:** https://github.com/wildecho94/rootrecord  
**RootRecord** — bootstrapping your ideas, one plugin at a time.