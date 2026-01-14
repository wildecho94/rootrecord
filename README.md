# RootRecord

Telegram bot + lightweight web dashboard for GPS tracking, vehicle management, fuel logging, MPG stats, and personal finance.

**Current Version:** v1.42.20260114 Beta  
**Status:** Core bot features stable • Finance, fill-up, and MPG management fully functional

## Highest Priority Features (Finance, MPG, Fill-up)

- **Fuel Logging (/fillup)**  
  Clean input-first flow (no initial buttons)  
  Format: `gallons price [odometer if full tank]`  
  Examples:  
  - `12.5 45.67 65000` → full tank  
  - `10.2 38.90` → partial fill-up  
  Vehicle confirmation buttons → saves to `fuel_records` + auto expense to `finance_records` (linked via vehicle_id)  
  Full tanks trigger MPG calculation

- **MPG Statistics (/mpg)**  
  Per-vehicle: last MPG + running average  
  Uses `initial_odometer` from `vehicles` table as baseline for first fill-up  
  Only calculates on full tanks with odometer  
  Accurate even after multiple partial fills between full tanks

- **Personal Finance (/finance)**  
  Log expense/income/debt/asset  
  View balance & net worth  
  Auto fuel expenses from fill-ups (linked to vehicle)  
  All finance entries stored in `finance_records` with vehicle_id

## Other Features

- **Location & GPS**  
  Saves every ping (new + live edits)  
  Reverse geocoding via geopy (address, city, country)  
  Distance between pings

- **Vehicle Management**  
  `/vehicle add <Plate> <Year> <Make> <Model> <Odometer>`  
  `/vehicles` – list your vehicles + action buttons  
  Only shows your own vehicles (user_id filtered)

- **Uptime**  
  `/uptime` – lifetime stats across restarts/crashes

- **Web Dashboard**  
  Landing page (`index.html`) with usage guide + live stats cards  
  Public URLs: rootrecord.info, dashboard.rootrecord.info, www.rootrecord.info  
  Served via Flask + Cloudflare Tunnel (no open ports)  
  Stats pulled directly from database

## Commands Menu (BotFather /setcommands)
start - Welcome and get started
vehicles - List your vehicles
vehicle - Add a new vehicle
fillup - Log a fuel fill-up
mpg - View MPG statistics
finance - Manage finances
uptime - Check bot uptime
web - Get link to web dashboard
text## Current Known Issues & Adjustments Needed

### Critical (breaking core features)
- Duplicate bot polling / getUpdates conflict  
  → Telegram error: "terminated by other getUpdates request"  
  → Multiple instances polling simultaneously

- Flask origin connection refused / 502 on public URLs  
  → Tunnel connected, but localhost:5000 refuses connection → Flask not running or not bound correctly

- Stats cards show "—" or "N/A"  
  → /totals.json returns 503 or empty → DB tables missing/empty → totals_plugin or app.py can't count

### High Priority (major usability/reliability)
- No real login / session system  
  → Dummy credentials → web dashboard not tied to Telegram users

- DB schema missing tables  
  → "no such table: pings", "activity_sessions", etc. → totals always 0

- Hardcoded paths (DB, credentials)  
  → Breaks if project moved

- Flask dev server warning  
  → Not production-ready (single-threaded, insecure)

### Medium Priority
- Public URLs inconsistent (some work, dashboard 502)  
  → Possible DNS, ingress rule, or Flask stability issue

- Multiple cmd windows clutter  
  → Bat opens "Web + Tunnel" + main → could be one window

- No per-user filtering on web  
  → Dashboard shows global totals

- No error messages on web  
  → 503 → cards stay "—" with no feedback

### Low Priority / Polish
- Tutorial in index.html mentions /web command → not fully implemented
- No favicon, meta tags, mobile optimization
- No rate limiting on /totals.json
- No HTTPS on local dev (mixed content on public HTTPS)
- No version check / auto-update notice
- No Telegram command to restart tunnel/Flask

Bot core is stable (plugins load, polling works).  
Finance, fill-up, and MPG management are **fully functional** in the bot.  
Web dashboard is live but basic (static landing + broken stats).

Next priorities: fix duplicate polling, get Flask stable on public URLs, make totals read from DB correctly.