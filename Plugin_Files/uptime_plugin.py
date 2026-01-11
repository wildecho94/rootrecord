# Plugin_Files/uptime_plugin.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - single-file version with periodic terminal update

Every 60 seconds (and once on startup):
- Calculates total uptime, total downtime, and percentage from raw DB events
- Prints stats in yellow to terminal
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

# Initialize DB
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                uptime_seconds INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

# Get all events sorted by time
def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC").fetchall()
    return [(typ, datetime.fromisoformat(ts)) for typ, ts in rows]

# Calculate uptime stats from raw events
def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {
            "total_uptime": "0:00:00",
            "total_downtime": "0:00:00",
            "uptime_pct": "100.000"
        }

    now = datetime.utcnow()
    total_uptime = timedelta(0)
    total_downtime = timedelta(0)
    last_time = None
    in_uptime = False

    for typ, ts in events:
        if last_time is not None:
            delta = ts - last_time
            if in_uptime:
                total_uptime += delta
            else:
                total_downtime += delta

        if typ == "start":
            in_uptime = True
        elif typ in ("stop", "crash"):
            in_uptime = False

        last_time = ts

    # Current ongoing session
    if in_uptime and last_time:
        current = now - last_time
        total_uptime += current

    total_time = total_uptime + total_downtime
    pct = 100.000 if total_time.total_seconds() == 0 else (total_uptime / total_time * 100)

    return {
        "total_uptime": str(total_uptime),
        "total_downtime": str(total_downtime),
        "uptime_pct": f"{pct:.3f}"
    }

# Print stats in yellow
def print_uptime_stats():
    s = calculate_uptime_stats()
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    line = f"{YELLOW}[UPTIME] {now_str} | Total Up: {s['total_uptime']} | " \
           f"Total Down: {s['total_downtime']} | Uptime: {s['uptime_pct']}%{RESET}"
    print(line)

# Periodic printer (every 60 seconds)
async def periodic_printer():
    while True:
        print_uptime_stats()
        await asyncio.sleep(60)

# Command handler
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = calculate_uptime_stats()
    text = (
        f"**Uptime Stats**\n"
        f"• Total uptime ever: {s['total_uptime']}\n"
        f"• Total downtime: {s['total_downtime']}\n"
        f"• Uptime percentage: {s['uptime_pct']}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# Startup
init_db()

with sqlite3.connect(DB_PATH) as conn:
    conn.execute("INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
                 ("start", datetime.utcnow().isoformat()))
    conn.commit()

# Print stats immediately on startup
print_uptime_stats()

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
    asyncio.create_task(periodic_printer())