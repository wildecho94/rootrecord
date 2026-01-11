# Plugin_Files/uptime_plugin.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - single-file version with periodic terminal update

Displays/updates uptime/downtime + percentage every 10 seconds in yellow.
Saves every single piece of data (current, total up/down, pct) to DB every 10s.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Paths
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"
STATE_PATH = ROOT / "uptime_state.json"

# Colors
YELLOW = "\033[93m"
RESET  = "\033[0m"

# Initialize DB with separate columns for every value
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uptime_stats (
                timestamp TEXT PRIMARY KEY,
                current_uptime_sec INTEGER,
                total_uptime_sec INTEGER,
                total_downtime_sec INTEGER,
                uptime_percentage REAL,
                current_uptime_str TEXT,
                total_uptime_str TEXT,
                total_downtime_str TEXT
            )
        ''')
        conn.commit()

# State
def load_state():
    if STATE_PATH.exists():
        try:
            with STATE_PATH.open("r") as f:
                data = json.load(f)
                return {
                    "last_start": datetime.fromisoformat(data["last_start"]) if data.get("last_start") else None,
                    "last_end": datetime.fromisoformat(data["last_end"]) if data.get("last_end") else None,
                    "total_uptime": timedelta(seconds=data.get("total_uptime", 0)),
                    "total_downtime": timedelta(seconds=data.get("total_downtime", 0))
                }
        except Exception as e:
            print(f"[uptime] State load failed: {e}")
    return {"last_start": None, "last_end": None, "total_uptime": timedelta(0), "total_downtime": timedelta(0)}

def save_state(last_start, last_end, total_uptime, total_downtime):
    data = {
        "last_start": last_start.isoformat() if last_start else None,
        "last_end": last_end.isoformat() if last_end else None,
        "total_uptime": int(total_uptime.total_seconds()),
        "total_downtime": int(total_downtime.total_seconds())
    }
    try:
        with STATE_PATH.open("w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[uptime] State save failed: {e}")

# Get current stats (all pieces)
def get_stats():
    state = load_state()
    now = datetime.utcnow()
    current = now - state["last_start"] if state["last_start"] else timedelta(0)
    total_up = state["total_uptime"] + current
    total_time = total_up + state["total_downtime"]
    pct = 100.0 if total_time.total_seconds() == 0 else (total_up / total_time * 100)

    return {
        "now": now,
        "current_sec": int(current.total_seconds()),
        "total_up_sec": int(total_up.total_seconds()),
        "total_down_sec": int(state["total_downtime"].total_seconds()),
        "uptime_pct": pct,
        "current_str": str(current),
        "total_up_str": str(total_up),
        "total_down_str": str(state["total_downtime"])
    }

# Periodic printer + DB save (every 10 seconds)
async def periodic_printer():
    while True:
        s = get_stats()
        line = f"{YELLOW}[UPTIME] {s['now'].strftime('%H:%M:%S')} | " \
               f"Current: {s['current_str']} ({s['current_sec']}s) | " \
               f"Total Up: {s['total_up_str']} ({s['total_up_sec']}s) | " \
               f"Total Down: {s['total_down_str']} ({s['total_down_sec']}s) | " \
               f"Pct: {s['uptime_pct']:.1f}%{RESET}"
        print(line)

        # Save EVERY piece to database
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO uptime_stats 
                (timestamp, current_uptime_sec, total_uptime_sec, total_downtime_sec, 
                 uptime_percentage, current_uptime_str, total_uptime_str, total_downtime_str)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s['now'].isoformat(),
                s['current_sec'],
                s['total_up_sec'],
                s['total_down_sec'],
                s['uptime_pct'],
                s['current_str'],
                s['total_up_str'],
                s['total_down_str']
            ))
            conn.commit()

        await asyncio.sleep(10)

# Command
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = get_stats()
    text = (
        f"**Uptime Stats**\n"
        f"• Current session: {s['current_str']} ({s['current_sec']}s)\n"
        f"• Total uptime ever: {s['total_up_str']} ({s['total_up_sec']}s)\n"
        f"• Total downtime: {s['total_down_str']} ({s['total_down_sec']}s)\n"
        f"• Uptime percentage: {s['uptime_pct']:.1f}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# Startup
last_start = datetime.utcnow()
init_db()

with sqlite3.connect(DB_PATH) as conn:
    conn.execute("INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
                 ("start", datetime.utcnow().isoformat()))
    conn.commit()

# Graceful shutdown
import atexit
def on_exit():
    now = datetime.utcnow()
    current = now - last_start
    state = load_state()
    new_up = state["total_uptime"] + current
    save_state(state["last_start"], now, new_up, state["total_downtime"])
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO uptime_records (event_type, timestamp, uptime_seconds) VALUES (?, ?, ?)",
                     ("stop", now.isoformat(), int(current.total_seconds())))
        conn.commit()
atexit.register(on_exit)

# Registration
def register_commands(app: Application):
    app.add_handler(CommandHandler("uptime", uptime))
    print("[uptime_plugin] /uptime registered")
    # Start periodic printer
    asyncio.create_task(periodic_printer())