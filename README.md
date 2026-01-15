**v1.42.20260113 – Major Update – Fully Working Vehicle & Fuel Tracking**

This release completes the entire core feature set originally described in [#1](https://github.com/wildecho94/rootrecord/issues/1). All requested functionality is now implemented, tested, and stable.

### What's included (all items from #1 completed)

- `/vehicle add <Plate> <Year> <Make> <Model> <Odometer>`  
  → Adds vehicle with robust parsing (multi-word models OK, year/odometer validated)

- `/vehicles`  
  → Lists only your vehicles with action buttons (View MPG, Add New)

- `/fillup` – **new simple & clean flow** (no initial button spam)  
  1. Prompt: "Enter fill-up: gallons price [odometer if full tank]"  
  2. Reply with numbers (e.g. `12.5 45.67 65000` or `10.2 38.90`)  
  3. Confirmation buttons show only your vehicles  
  4. Tap vehicle → saves fill-up to `fuel_records` + expense to `finance_records`

- `/mpg` – per-vehicle stats  
  → Shows last MPG + average  
  → Uses `initial_odometer` from `vehicles` table as baseline for first fill-up MPG  
  → Safe handling for missing data (no crashes on None values)

- MPG calculation  
  → Only on full tanks (odometer provided)  
  → First fill-up uses `initial_odometer` → current odometer difference / gallons  
  → Subsequent fills use previous fill's odometer

- Auto-log fuel expense in `finance_records`  
  → Type: expense  
  → Amount: price  
  → Description: "Fuel fill-up: X gal @ $Y.YY"  
  → Linked to `vehicle_id`

- All queries filter by user_id → only shows your own vehicles

- Clean chat flow → input first, confirm vehicle second, no unnecessary buttons

- Registration split:  
  - `vehicles_plugin.py`: management + MPG  
  - `fillup_plugin.py`: fill-up logging + confirmation flow

### Changelog summary (v1.42.20260113)

- Major feature completion: full vehicle add/list/fill-up/MPG/finance integration
- New isolated `fillup_plugin.py` (input first → confirm vehicle → save)
- Fixed `/mpg` TypeError on None values
- Added `initial_odometer` as baseline for first fill-up MPG
- Removed old fill-up code from `vehicles_plugin.py`
- Improved registration in `telegram_plugin.py` (no command conflicts)
- All commands tested end-to-end in private chat

Bot is now **fully working** for the original scope in #1.

Feel free to test and report any edge cases. 🚗⛽