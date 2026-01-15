# RootRecord

**Personal tracking bot & dashboard**  
RootRecord is a modular Telegram bot + Flask web dashboard for logging GPS pings (with reverse geocoding), vehicle fuel fill-ups (MPG & cost per mile), finance transactions, system uptime, and more.

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

Built in Python with SQLite, python-telegram-bot, Flask, Geopy, and Cloudflare Tunnel.

Current version: **1.43.20260117**

## Features

### Telegram Bot
- Live location → auto-save GPS + reverse geocode
- Vehicle management: `/vehicles`, `/vehicle add`
- Fuel logging: `/fillup` → auto expense log
- MPG & fuel cost stats: `/mpg` → cumulative, total $/mile
- Finance: `/finance` → inline button menu + detailed reports
- Uptime: `/uptime` → lifetime stats

### Web Dashboard
- Flask serving `index.html` + `/totals.json`
- Cloudflare Tunnel for public access

### Backend
- SQLite (`data/rootrecord.db`)
- Auto-backups on startup (skips `.db-shm`/`.db-wal` + `.zip`)
- Plugin auto-discovery from `Plugin_Files/`

## Setup

1. Clone repo
2. `pip install python-telegram-bot geopy flask`
3. Create `config_telegram.json` with bot token
4. Run `start_rootrecord.bat`

## Hardware Notes

- **Dell OptiPlex 7060** – low-power, reliable 24/7 host
- **Blockchain nodes**: Full LTC and DOGE chains synced and running in background (adds significant disk I/O and storage usage – blockchains grow ~50–100 GB/year each)
- **USB dock/enclosure** – dual-slot, handles D: recycled SSD
- **L: drive** – large internal SATA drive for desktop (direct motherboard connection, bulk archive + possibly blockchain data)

MIT License @wildecho94