# Plugin_Files/uptime_plugin.py
# Version: 20260113 – Merged + fixed lifetime calculation, single-file

"""
Uptime plugin – single-file, reliable lifetime tracking

Tracks start/stop/crash events, calculates true uptime percentage across all runs.
Prints stats every 60s in yellow + saves snapshot to uptime_stats table.
Adds /uptime command.
Handles crashes/restarts properly (unpaired start = still running).
"""

import threading
import time
import sqlite3
import atexit
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ────────────────────────────────────────────────
# Colors & Paths
# ────────────────────────────────────────────────
YELLOW = "\033[93m"
RESET  = "\033[0m"

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

# ────────────────────────────────────────────────
# Database Setup
# ────────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,           -- start, stop, crash
                timestamp TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS uptime_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_uptime_sec INTEGER,
                total_downtime_sec INTEGER,
                uptime_percentage REAL
            )
        ''')
        conn.commit()
    print("[uptime_plugin] Database tables ready")

# ────────────────────────────────────────────────
# Core Logic – calculate true lifetime uptime
# ────────────────────────────────────────────────
def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC"
        ).fetchall()
    return [(typ, datetime.fromisoformat(ts)) for typ, ts in rows]

def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {"total_up_sec": 0, "total_down_sec": 0, "uptime_pct": 100.0, "status": "never_started"}

    now = datetime.utcnow()
    total_up = timedelta(0)
    total_down = timedelta(0)
    last_time = events[0][1]  # start from first event
    is_running = False

    for typ, ts in events:
        if last_time is not None:
            delta = ts - last_time
            if is_running:
                total_up += delta
            else:
                total_down += delta

        if typ == "start":
            is_running = True
        elif typ in ("stop", "crash"):
            is_running = False

        last_time = ts

    # If still running at the end (no final stop/crash), count until now
    if is_running and last_time:
        current_up = now - last_time
        total_up += current_up

    total_time = total_up + total_down
    uptime_pct = 100.0 if total_time.total_seconds() == 0 else (total_up.total_seconds() / total_time.total_seconds() * 100)

    status = "running" if is_running else "stopped"

    return {
        "total_up_sec": int(total_up.total_seconds()),
        "total_down_sec": int(total_down.total_seconds()),
        "uptime_pct": uptime_pct,
        "status": status,
        "last_event_time": last_time.isoformat() if last_time else None
    }

# ────────────────────────────────────────────────
# Print in yellow + save snapshot
# ────────────────────────────────────────────────
def print_uptime_stats(s):
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    up_str = str(timedelta(seconds=s['total_up_sec']))
    down_str = str(timedelta(seconds=s['total_down_sec']))
    line = f"{YELLOW}[UPTIME] {now_str} | Up: {up_str} | Down: {down_str} | {s['uptime_pct']:.3f}% | Status: {s['status']}{RESET}"
    print(line)

def save_stats_snapshot(s):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO uptime_stats 
            (timestamp, total_uptime_sec, total_downtime_sec, uptime_percentage)
            VALUES (?, ?, ?, ?)
        ''', (now, s['total_up_sec'], s['total_down_sec'], s['uptime_pct']))
        conn.commit()

# ────────────────────────────────────────────────
# Periodic printer + saver (daemon thread)
# ────────────────────────────────────────────────
def periodic_update():
    print("[uptime_plugin] Periodic thread started (every 60s)")
    while True:
        s = calculate_uptime_stats()
        print_uptime_stats(s)
        save_stats_snapshot(s)
        time.sleep(60)

# ────────────────────────────────────────────────
# /uptime command
# ────────────────────────────────────────────────
async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = calculate_uptime_stats()
    up_str = str(timedelta(seconds=s['total_up_sec']))
    down_str = str(timedelta(seconds=s['total_down_sec']))
    text = (
        f"**Uptime Statistics**\n"
        f"• Status: **{s['status'].upper()}**\n"
        f"• Total uptime: {up_str}\n"
        f"• Total downtime: {down_str}\n"
        f"• Uptime percentage: **{s['uptime_pct']:.3f}%**\n"
        f"• Last event: {s['last_event_time'] or 'N/A'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ────────────────────────────────────────────────
# Startup + shutdown
# ────────────────────────────────────────────────
init_db()

# Record start on every launch
with sqlite3.connect(DB_PATH) as conn:
    conn.execute(
        "INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
        ("start", datetime.utcnow().isoformat())
    )
    conn.commit()

# Initial print + save
s = calculate_uptime_stats()
print_uptime_stats(s)
save_stats_snapshot(s)

# Start periodic thread
thread = threading.Thread(target=periodic_update, daemon=True)
thread.start()

# Graceful shutdown: record stop/crash
def on_shutdown():
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO uptime_records (event_type, timestamp) VALUES (?, ?)",
            ("stop", now)
        )
        conn.commit()
    print("[uptime_plugin] Shutdown recorded")

atexit.register(on_shutdown)

# Register command
def register(app: Application):
    app.add_handler(CommandHandler("uptime", cmd_uptime))
    print("[uptime_plugin] /uptime command registered")