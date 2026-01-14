# RootRecord

Telegram bot + lightweight web dashboard for GPS tracking, vehicle management, fuel logging, MPG stats, and personal finance.

**Current Version:** v1.42.20260114 Beta  
**Status:** Core features complete and stable (bot + tunnel + web landing page)

## Features

- **Location & GPS**  
  Saves every ping (new messages + live location edits)  
  Reverse geocoding (address, city, country) via geopy  
  Distance between pings

- **Vehicle Management**  
  `/vehicle add <Plate> <Year> <Make> <Model> <Odometer>`  
  `/vehicles` – list your vehicles + action buttons  
  Only shows vehicles owned by you (user_id filtered)

- **Fuel Logging**  
  `/fillup` – input-first flow: `gallons price [odometer if full tank]`  
  Vehicle confirmation buttons → saves to `fuel_records` + expense to `finance_records`  
  Full tanks trigger MPG calculation

- **MPG Stats**  
  `/mpg` – per-vehicle last MPG + running average  
  Uses `initial_odometer` as baseline for first fill-up  
  Only calculates on full tanks with odometer

- **Personal Finance**  
  `/finance` – log expense/income/debt/asset  
  View balance & net worth  
  Auto fuel expenses from fill-ups (linked via vehicle_id)

- **Uptime**  
  `/uptime` – lifetime stats across restarts/crashes

- **Web Dashboard**  
  Landing page (`index.html`) with usage guide + live stats cards  
  Public URLs: rootrecord.info, dashboard.rootrecord.info, www.rootrecord.info  
  Served via Flask + Cloudflare Tunnel (no open ports)  
  Stats pulled directly from database (users, pings, vehicles, fillups, finance, activities)

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

### Critical
- Duplicate bot polling / getUpdates conflict  
  → Telegram error: "terminated by other getUpdates request"  
  → Multiple instances polling at once (likely core.py + telegram_plugin.py overlap)

- Flask origin refused / public URLs 502  
  → Tunnel connected, but localhost:5000 refuses connection → Flask not running or not bound correctly

- Stats cards show "—" or "N/A"  
  → /totals.json returns 503 or empty → DB tables missing/empty → totals_plugin or app.py can't count

- totals_plugin.py fails to load ("No module named 'utils'")  
  → Plugin doesn't run → no periodic totals updates

### High Priority
- No real login / session system  
  → Dummy test credentials → web dashboard not tied to Telegram users

- DB schema missing tables  
  → "no such table: pings", "activity_sessions", etc. → totals always 0

- Hardcoded paths (DB, credentials, etc.)  
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

- Uptime calculation inconsistent  
  → Shows odd up/down times

### Low Priority / Polish
- Tutorial in index.html mentions /web command → not fully implemented
- No favicon, meta tags, mobile optimization
- No rate limiting on /totals.json
- No HTTPS on local dev (mixed content warnings)
- No version check / auto-update notice
- No way to restart tunnel/Flask from Telegram

Bot core is stable (plugins load, polling works).  
Web dashboard is live but basic (static landing + broken stats).  
Next priorities: fix duplicate polling, get Flask stable on public URLs, make totals read from DB correctly.

Enjoy! 🚀  
Report bugs or ideas in issues.