# RootRecord
v1.42.20260112-2 – Second build of the day

Self-bootstrapping, modular Python plugin system + Telegram bot framework  
Designed for personal automation, bots, GPS tracking, uptime monitoring, and extensibility.

Current State (as of Jan 13 2026)
- Fully working Telegram bot with live location tracking
- Every ping (initial location + all live edits) saved to database
- Reliable uptime tracking across restarts/crashes
- Auto-backup, debug logging, folder setup, pycache cleaning
- GitHub auto-publish (optional – high risk if token is present)
- Centralized asyncio scheduler
- Plugin auto-discovery & loading

Quick Start

1. Clone or download:
   git clone https://github.com/wildecho94/rootrecord.git
   cd rootrecord

2. Install dependencies:
   pip install python-telegram-bot httpx

3. Create config_telegram.json in root (do not commit!):
   {
     "bot_token": "your_bot_token_here"
   }

4. Run:
   python core.py
   # or on Windows: double-click start_rootrecord.bat

The bot starts polling. Send /start or a live location to test.

Key Features

- Plugin System
  - Auto-discovers all .py files in Plugin_Files/
  - Calls initialize() if present
  - Supports single-file and split plugins

- Telegram Bot (telegram_plugin.py)
  - Loads token from config_telegram.json
  - Auto-registers /start
  - Saves every live location ping to gps_records
  - Handles new locations + edited live messages
  - Verbose logging of all messages/commands

- Uptime Monitoring (uptime_plugin.py)
  - Tracks start/stop/crash events
  - Calculates true lifetime uptime percentage
  - Prints yellow stats every 60 seconds
  - Saves periodic snapshots to uptime_stats
  - /uptime command shows current lifetime stats

- Self-Maintenance
  - Clears __pycache__ folders on startup
  - Creates timestamped code/data backups
  - Optional auto-commit & push to GitHub (use carefully!)
  - Centralized asyncio loop + scheduler

- Database (data/rootrecord.db)
  - gps_records: every ping (lat, lon, accuracy, heading, timestamp, received_at)
  - uptime_records: start/stop/crash events
  - uptime_stats: periodic snapshots

Security – Important!

Never commit or share:
- config_telegram.json (contains bot token)
- publish_rootrecord.py (contains GitHub token if used)
- __pycache__/, backups, logs, .db files

Recommended .gitignore additions:
config_*.json
publish_*.py
*.secrets.*
backups/
__pycache__/
*.db
*.log

Folder Structure

rootrecord/
├── Core_Files/           # scheduler, shared logic
├── Handler_Files/        # message/command handlers
├── Plugin_Files/         # plugins (telegram_plugin.py, uptime_plugin.py, ...)
├── commands/             # Telegram commands (start_cmd.py, ...)
├── data/                 # rootrecord.db (SQLite)
├── backups/              # auto backups
├── debug_rootrecord.log  # console mirror
├── core.py               # main entry
├── start_rootrecord.bat  # Windows launcher
└── README.md

Roadmap – Next Steps

Immediate / this week
- Hot-reload for plugins
- Better crash detection (auto "crash" on unclean shutdown)
- Expose scheduler to plugins
- /gps command (recent pings or map link)

Medium term
- Multi-platform (Discord?)
- Plugin template gallery
- Self-healing (auto-restart on crash)
- GPS export to GPX/KML

Long term
- AI agent hooks
- Visual dashboard (Telegram mini-app or web)
- Voice/image recognition

Contact / Contribute

Early personal project – feedback, issues, PRs welcome!

GitHub: https://github.com/wildecho94/rootrecord
X: @wildecho94