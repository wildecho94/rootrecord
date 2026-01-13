# RootRecord
v1.42.20260112-2 – Test version

Simple modular Python bot framework with Telegram integration.

Current working features:
- Telegram bot: sends /start reply, receives messages
- Live location tracking: every new ping + all edits saved to gps_records table
- Uptime tracking: logs start/stop, calculates lifetime %, prints every 60s in yellow
- /uptime command shows current stats
- Auto-backup of code/data on startup
- Debug log mirrors console to file
- Graceful shutdown logs "stop" event

What we're working on next (v20260113 target):
- Geopy plugin: reverse geocoding + distance between pings
  - All enriched data saved separately (new table)
  - Uses original raw timestamps from gps_records
- Finance plugin: expense, income, debt, asset logging
  - Single table for all finance records
  - Auto-categories on first use
  - /finance command with sub-operations (balance, networth, etc.)
- Vehicles plugin: multi-vehicle support + fuel fill-ups
  - Single table for vehicles and fuel records
  - Fill-ups auto-log as expense in finance table
  - MPG calculations per vehicle

Repo: https://github.com/wildecho94/rootrecord
Bot: @RootRecordCore_bot

Early test project – more coming soon.