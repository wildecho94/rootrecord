# RootRecord

**Modular Python plugin system with auto-maintained templates**  
Version: v1.42.20260111  
Status: Early development / active bootstrapping (January 11, 2026)

RootRecord is a lightweight, extensible framework designed for building modular Python applications, especially bots and automation tools, using a plugin-based architecture.

### Current Features (as of Jan 11, 2026)

- **Automatic folder & file preparation**
  - Creates `Core_Files/`, `Handler_Files/`, `Plugin_Files/` with `__init__.py`
  - Generates blank plugin template if missing

- **Startup safety features**
  - Clears `__pycache__` folders
  - Creates timestamped backups (skips `.zip` files)
  - Logs everything to `debug_rootrecord.log` (console mirrored)

- **Plugin auto-discovery & loading**
  - Detects plugins in `Plugin_Files/*.py`
  - Supports single-file or split (main / core / handler) plugins
  - Calls `initialize()` if present

- **Telegram integration** (working bot)
  - Loads token from `config_telegram.json`
  - Auto-creates `/start` command
  - Real-time logging of all incoming messages/commands
  - Background polling with drop pending updates

- **Uptime plugin** (single-file)
  - Tracks total uptime/downtime from `start`/`stop`/`crash` events
  - Calculates percentage ratio from raw database events
  - Prints yellow stats every 60 seconds + on startup
  - Saves snapshots to `uptime_stats` table

- **GitHub auto-publish** (`publish_rootrecord.py`)
  - Commits & pushes changes on startup
  - Handles deleted/moved files (`git add -u`)

- **Centralized asyncio loop**
  - Reliable background tasks without starvation
  - All console output logged & mirrored

Changelog
v1.42.20260111 (Jan 11, 2026)

Added Core_Files/scheduler.py for centralized periodic task management
All console output now mirrored & saved to debug_rootrecord.log
Uptime plugin: reliable 60-second stats print + DB snapshot
Telegram: detailed logging of config, commands, polling, updates
Core: asyncio main loop for stable background tasks

v1.42.20260110 (previous)

Initial bootstrap with folder prep, backups, plugin discovery
Telegram plugin with /start command & message logging
Basic uptime plugin with DB & JSON state
GitHub auto-publish with deleted file handling

Earlier versions (pre-20260110)

Project initialization
SQLite database setup
Backup system with zip skip
Blank plugin template generator

Goals & Roadmap (2026)
Short-term

Stabilize uptime & telegram plugins
Add crash detection & recovery logging
Implement proper shutdown hooks
Expose scheduler to all plugins

Medium-term

Plugin hot-reload support
Command prefix & argument parsing
User/session tracking in DB
Multi-platform support (Discord?)

Long-term vision

Self-healing framework
Plugin marketplace
AI agent integration
Enterprise-grade logging & monitoring

Security Notes

Never commitconfig_telegram.json or any secrets
publish_rootrecord.py contains GitHub token → delete after use
Regenerate Telegram token if ever exposed

Contributing
Early stage project — breaking changes expected.
Focus: stability > features