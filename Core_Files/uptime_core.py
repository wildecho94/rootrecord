# RootRecord Core_Files/uptime_core.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - core logic & database interaction
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "rootrecord.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                uptime_seconds INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT event_type, timestamp FROM uptime_records ORDER BY id ASC").fetchall()
    return [(typ, datetime.fromisoformat(ts)) for typ, ts in rows]

def calculate_uptime_stats():
    events = get_all_events()
    if not events:
        return {"total_up_sec": 0, "total_down_sec": 0, "uptime_pct": 100.000}

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

    if in_uptime and last_time:
        current = now - last_time
        total_up += current

    total_time = total_up + total_down
    pct = 100.000 if total_time.total_seconds() == 0 else (total_up / total_time * 100)

    return {
        "total_up_sec": int(total_up.total_seconds()),
        "total_down_sec": int(total_down.total_seconds()),
        "uptime_pct": pct
    }

init_db()