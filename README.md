# RootRecord
**Personal tracking bot & dashboard**  
**Current version: 1.42**  
**Latest release: 20260117** (January 17, 2026)

RootRecord is a modular Telegram bot + Flask web dashboard for logging real-time GPS pings (with reverse geocoding), vehicle fuel fill-ups (MPG & $/mile stats), finance transactions, system uptime, and more.

- **Host machine**: Dell OptiPlex 7060 (Albuquerque, NM)  
- **CPU**: Intel Core i5-8500T @ 2.10 GHz (6 cores, 35W TDP)  
- **RAM**: 32 GB (31.8 GB usable)  
- **OS**: Windows 11 Pro 24H2 (build 26200.7623)  
- **Additional background services**:  
  - Full Litecoin (LTC) blockchain node (kept synced)  
  - Full Dogecoin (DOGE) blockchain node (kept synced)  
  - Both run continuously in the background  
- **Storage layout**:  
  - **C:** (Local Disk) – 118 GB flat M.2 SSD chip (moved from laptop, OS + program files, ~20 GB free)  
  - **D:** (Storage) – 1.81 TB portable SSD (recycled, connected via USB dock/enclosure)  
  - **L:** (Archive) – 3.63 TB large internal desktop SATA drive (2.10 TB free, direct to motherboard SATA port)  
  - **USB dock note**: Dual-slot enclosure supporting micro SSDs or full-size SATA drives (currently handling D:; L: is internal SATA)

Built in Python with MySQL (v9.5.0), python-telegram-bot, SQLAlchemy async, Flask, Geopy, and Cloudflare Tunnel.

### Features

#### Telegram Bot
- Live location → auto-save GPS ping + reverse geocode  
- Vehicle management: `/vehicles`, `/vehicle add PLATE YEAR MAKE MODEL ODOMETER`  
- Fuel logging: `/fillup` (gallons, price, odometer, full/partial)  
- MPG & fuel cost stats: `/mpg` (cumulative, total $/mile)  
- Finance: `/finance` → inline button menu + reports  
- Uptime: `/uptime` → lifetime stats  
- `/start` — Registers user (if new) + shows welcome with full command list & project overview

#### Web Dashboard
- Flask serving `index.html` + `/totals.json`  
- Cloudflare Tunnel for public access

#### Backend
- MySQL (localhost, v9.5.0) – primary storage  
- SQLite (`data/rootrecord.db`) – legacy fallback (backups disabled)  
- Plugin auto-discovery from `Plugin_Files/`

### Setup
1. Clone repo
2. `pip install python-telegram-bot geopy flask sqlalchemy asyncmy mysql-connector-python`
3. Create `config_telegram.json` with bot token
4. Run `start_rootrecord.bat`

### Timing Perspective (Jan 17, 2026)
RootRecord has been running continuously for **3 days, 16+ hours** (as of this release) with **~98.1% uptime**.  
The bot has survived multiple restarts, git history purges (to kill massive backup zips), full MySQL migration, and countless code tweaks — all while keeping LTC and DOGE nodes synced in the background.  
It's still early — many features are stubbed or in progress — but the core loop (polling + DB + plugins) is stable.

### Releases
- **20260116** (January 16, 2026) — Initial public release  
  → https://github.com/wildecho94/rootrecord/releases/tag/20260116

MIT License @wildecho94