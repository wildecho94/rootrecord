# Plugin_Files/uptime_plugin.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - single-file version with periodic terminal update

Every 60 seconds (and once on startup):
- Calculates total uptime, total downtime, and percentage from raw DB events
- Prints stats in yellow to terminal
- Writes calculated values to uptime_stats table every time
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, Application

# Paths
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

# Colors
YELLOW = "\033[93m"
RESET  = "\033[0m"

# Initialize DB tables
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Events table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                uptime_seconds INTEGER DEFAULT 0
            )
        ''')
        # Stats snapshot table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uptime_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_uptime_sec INTEGER,
                total_downtime_sec INTEGER,
                uptime_percentage REAL
            )
        ''')
        conn.commit()

# Get all events sorted by time
def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC").fetchall()
    return [(typ, datetime.fromisoformat(ts)) for typ, ts in rows]

# Calculate stats from raw events
def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {"total_up_sec": 0, "total_down_sec": 0, "uptime_pct": 100.0}

    now = datetime.utcnow()
    total_up = timedelta(0)
    total_down = timedelta(0)
    last_time = None
    in_uptime = False

    for typ, ts in events:
        if last_time is not None:
            delta = ts - last_time
            if in_uptime:
                total_up += delta
            else:
                total_down += delta

        if typ == "start":
            in_uptime = True
        elif typ in ("stop", "crash"):
            in_uptime = False

        last_time = ts

    # Current session
    if in_uptime and last_time:
        current = now - last_time
        total_up += current

    total_time = total_up + total_down
    pct = 100.0 if total_time.total_seconds() == 0 else (total_up / total_time * 100)

    return {
        "total_up_sec": int(total_up.total_seconds()),
        "total_down_sec": int(total_down.total_seconds()),
        "uptime_pct": pct
    }

# Print stats in yellow
def print_uptime_stats(s):
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    line = f"{YELLOW}[UPTIME] {now_str} | Total Up: {timedelta(seconds=s['total_up_sec'])} | " \
           f"Total Down: {timedelta(seconds=s['total_down_sec'])} | " \
           f"Uptime: {s['uptime_pct']:.3f}%{RESET}"
    print(line)

# Save stats snapshot to DB
def save_stats_to_db(s):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO uptime_stats 
            (timestamp, total_uptime_sec, total_downtime_sec, uptime_percentage)
            VALUES (?, ?, ?, ?)
        ''', (now, s['total_up_sec'], s['total_down_sec'], s['uptime_pct']))
        conn.commit()

# Periodic update (every 60 seconds)
async def periodic_uptime_update():
    while True:
        s = calculate_uptime_stats()
        print_uptime_stats(s)
        save_stats_to_db(s)
        await asyncio.sleep(60)

# Command handler
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = calculate_uptime_stats()
    text = (
        f"**Uptime Stats**\n"
        f"• Total uptime ever: {timedelta(seconds=s['total_up_sec'])}\n"
        f"• Total downtime: {timedelta(seconds=s['total_down_sec'])}\n"
        f"• Uptime percentage: {s['uptime_pct']:.3f}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# Startup
init_db()

with sqlite3.connect(DB_PATH) as conn:
    conn.execute("INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
                 ("start", datetime.utcnow().isoformat()))
    conn.commit()

# Initial stats print + save
s = calculate_uptime_stats()
print_uptime_stats(s)
save_stats_to_db(s)

# Graceful shutdown
import atexit
def on_exit():
    now = datetime.utcnow()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
                     ("stop", now.isoformat()))
        conn.commit()
atexit.register(on_exit)

# Registration
def register_commands(app: Application):
    app.add_handler(CommandHandler("uptime", uptime))
    print("[uptime_plugin] /uptime registered")
    asyncio.create_task(periodic_uptime_update())