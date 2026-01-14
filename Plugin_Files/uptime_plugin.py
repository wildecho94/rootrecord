# Plugin_Files/uptime_plugin.py
# Version: 20260113 – Merged + fixed lifetime calculation, single-file

"""
Uptime plugin – single-file, reliable lifetime tracking

Tracks start/stop/crash events, calculates true uptime percentage across all runs.
Prints stats every 60s in yellow + saves snapshot to uptime_stats table.
Handles crashes/restarts properly (unpaired start = still running).
"""

import threading
import time
import sqlite3
import atexit
from datetime import datetime, timedelta
from pathlib import Path

YELLOW = "\033[93m"
RESET  = "\033[0m"

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

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

def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC")
        return c.fetchall()

def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {
            'total_up_sec': 0,
            'total_down_sec': 0,
            'uptime_pct': 0.0,
            'status': 'unknown',
            'last_event_time': None
        }

    total_up = 0
    total_down = 0
    start_time = None
    prev_end_time = None
    status = 'stopped'
    last_event_time = None

    for event_type, ts_str in events:
        last_event_time = ts_str
        ts = datetime.fromisoformat(ts_str)

        if event_type == 'start':
            if start_time is None:
                start_time = ts
                # If there was a previous stop, add gap as downtime
                if prev_end_time:
                    down_duration = (ts - prev_end_time).total_seconds()
                    if down_duration > 0:
                        total_down += down_duration
            status = 'running'
        elif event_type in ('stop', 'crash'):
            if start_time:
                up_duration = (ts - start_time).total_seconds()
                total_up += up_duration
                start_time = None
            prev_end_time = ts
            status = 'stopped'

    now = datetime.utcnow()
    if start_time:
        current_up = (now - start_time).total_seconds()
        total_up += current_up
        status = 'running'
    elif prev_end_time:
        # If currently stopped, add time since last stop as downtime
        current_down = (now - prev_end_time).total_seconds()
        total_down += current_down

    total_time = total_up + total_down
    uptime_pct = (total_up / total_time * 100) if total_time > 0 else 0.0

    return {
        'total_up_sec': int(total_up),
        'total_down_sec': int(total_down),
        'uptime_pct': uptime_pct,
        'status': status,
        'last_event_time': last_event_time
    }

def print_uptime_stats(stats):
    up_str = str(timedelta(seconds=stats['total_up_sec']))
    down_str = str(timedelta(seconds=stats['total_down_sec']))
    print(f"{YELLOW}[UPTIME] {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | "
          f"Up: {up_str} | Down: {down_str} | {stats['uptime_pct']:.3f}% | "
          f"Status: {stats['status']}{RESET}")

def save_stats_snapshot(stats):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO uptime_stats (timestamp, total_uptime_sec, total_downtime_sec, uptime_percentage)
            VALUES (?, ?, ?, ?)
        ''', (now, stats['total_up_sec'], stats['total_down_sec'], stats['uptime_pct']))
        conn.commit()

def periodic_update():
    while True:
        stats = calculate_uptime_stats()
        print_uptime_stats(stats)
        save_stats_snapshot(stats)
        time.sleep(60)

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

# Removed: def register(app) block – it was never called and can't be safely called here.
# Command will be moved to commands/uptime_cmd.py in next update so cmd_loader picks it up.