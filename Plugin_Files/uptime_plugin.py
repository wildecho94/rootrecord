# Plugin_Files/uptime_plugin.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - single-file version with periodic terminal update

Removes JSON state file.
Calculates uptime percentage using raw DB data (start/stop events).
Displays full stats in yellow every 10 seconds.
Saves current snapshot every 10 seconds.
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
                event_type TEXT NOT NULL,           -- 'start' / 'stop' / 'crash'
                timestamp TEXT NOT NULL,
                uptime_seconds INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

# Get all start/stop events sorted by time
def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC").fetchall()
    events = []
    for typ, ts in rows:
        events.append((typ, datetime.fromisoformat(ts)))
    return events

# Calculate current uptime, total up/down, percentage from raw events
def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {
            "current": "0:00:00",
            "total_uptime": "0:00:00",
            "total_downtime": "0:00:00",
            "uptime_pct": "100.0"
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

    # Current session
    if in_uptime and last_time:
        current = now - last_time
        total_uptime += current
    else:
        current = timedelta(0)

    total_time = total_uptime + total_downtime
    pct = 100.0 if total_time.total_seconds() == 0 else (total_uptime / total_time * 100)

    return {
        "current": str(current),
        "total_uptime": str(total_uptime),
        "total_downtime": str(total_downtime),
        "uptime_pct": f"{pct:.1f}"
    }

# Periodic printer (every 10 seconds)
async def periodic_printer():
    while True:
        s = calculate_uptime_stats()
        line = f"{YELLOW}[UPTIME] {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} | " \
               f"Current: {s['current']} | Total Up: {s['total_uptime']} | " \
               f"Total Down: {s['total_downtime']} | Pct: {s['uptime_pct']}%{RESET}"
        print(line)

        await asyncio.sleep(10)

# Command handler
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = calculate_uptime_stats()
    text = (
        f"**Uptime Stats**\n"
        f"• Current session: {s['current']}\n"
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

# Graceful shutdown (best-effort)
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