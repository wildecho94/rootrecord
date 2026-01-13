# RootRecord

Telegram bot for GPS tracking, vehicle management, fuel logging, MPG stats, and personal finance tracking.

## Current Version

**v1.42.20260114 Beta** – Major Update – Fully Working Core Features

This is the first major stable release after months of development and debugging.  
All original core functionality from issue #1 is now implemented, tested, and reliable.

## Features

- **GPS & Location Tracking**  
  Saves every ping (new messages + live location edits)  
  Auto reverse geocoding with geopy (address, city, country)  
  Distance from previous ping

- **Vehicle Management**  
  `/vehicle add <Plate> <Year> <Make> <Model> <Odometer>` – add vehicle  
  `/vehicles` – list your vehicles with action buttons (View MPG, Add New)  
  Only shows vehicles owned by you (filtered by user_id)

- **Fuel Logging (/fillup)**  
  Clean input-first flow: enter details → confirm vehicle → save  
  Simple format: `gallons price [odometer if full tank]`  
  Examples:  
  `12.5 45.67 65000` ← full tank  
  `10.2 38.90` ← partial fill-up  
  Saves to `fuel_records` + auto expense in `finance_records` (linked to vehicle)

- **MPG Statistics (/mpg)**  
  Per-vehicle: last MPG + running average  
  Uses `initial_odometer` from `vehicles` table as baseline for first fill-up MPG  
  Only calculates on full tanks (odometer provided)

- **Personal Finance (/finance)**  
  Log expense/income/debt/asset  
  View balance & net worth  
  Auto fuel expenses from fill-ups (linked to vehicle_id)

- **Uptime (/uptime)**  
  Lifetime tracking across restarts/crashes  
  Percentage uptime

## Commands Menu (BotFather /setcommands)
