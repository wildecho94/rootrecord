# RootRecord

**Personal tracking bot + dashboard**  
RootRecord is a self-hosted Telegram bot + lightweight web dashboard for logging and analyzing personal data: GPS location pings (with reverse geocoding), vehicle fuel fill-ups (MPG & cost per mile), finance/expenses (tied to vehicles), system uptime, and more.

Built in Python with SQLite backend, modular plugins, python-telegram-bot, Flask, and Cloudflare Tunnel for easy exposure.

Current version: **1.42.20260115** (January 2026)

## Features

- **Telegram Bot**  
  - Live location sharing → auto-saves GPS pings + reverse geocoding (via Geopy/Nominatim)  
  - Vehicle management: add/list vehicles with plate, year, make, model, initial odometer  
  - Fuel logging: gallons + price + optional odometer (full/partial tank) → auto-logs finance expense  
  - MPG & cost stats: cumulative MPG, total fuel cost, fuel $/mile (all fill-ups included)  
  - Finance tracking: /finance expense/income/debt/asset + balance/networth  
  - Uptime monitoring: lifetime uptime %, crash/restart tracking  
  - Inline buttons for vehicle selection & quick actions  

- **Web Dashboard** (via Flask + Cloudflare Tunnel)  
  - index.html served locally or via tunnel  
  - /totals.json endpoint for live stats (users, pings, vehicles, fillups, finance entries, etc.)  

- **Modular Plugin System**  
  - Plugins auto-discovered & initialized from `Plugin_Files/*.py`  
  - Easy to add new features (blank_plugin.py template included)  

- **Database**: SQLite (`data/rootrecord.db`)  
  - Tables for gps_records, fuel_records, finance_records, vehicles, uptime, geopy_enriched, etc.  

- **Reliability**  
  - Auto-backups on startup (skips .zip files)  
  - __pycache__ cleaning  
  - Verbose logging to console + `logs/debug_rootrecord.log`  

## Current Commands

- `/start` – Welcome message  
- `/vehicles` – List vehicles + inline buttons for details / MPG  
- `/vehicle add <Plate> <Year> <Make> <Model> <Odometer>` – Add a vehicle  
- `/fillup` – Log fuel fill-up (gallons price [odometer]) → vehicle selection  
- `/mpg` – Cumulative MPG, fuel cost, $/mile stats for all vehicles  
- `/finance expense <amount> <desc> [category]` – Log expense (also auto-logged from fillups)  
- `/finance balance` / `/finance networth`  
- `/uptime` – System lifetime uptime stats  

## Setup & Run

1. Clone repo  
   ```bash
   git clone https://github.com/wildecho94/rootrecord.git
   cd rootrecord