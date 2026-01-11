# RootRecord Core_Files/uptime_core.py
# Edited Version: 1.42.20260111

"""
Uptime plugin - core logic & database/JSON persistence
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "rootrecord.db"
STATE_PATH = Path(__file__).parent.parent / "uptime_state.json"

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

def record_event(event_type: str, uptime_sec: int = 0):
    ts = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO uptime_records (event_type, timestamp, uptime_seconds) VALUES (?, ?, ?)",
                     (event_type, ts, uptime_sec))
        conn.commit()

def get_stats():
    state = load_state()
    now = datetime.utcnow()
    current = now - state["last_start"] if state["last_start"] else timedelta(0)
    total_up = state["total_uptime"] + current
    total_time = total_up + state["total_downtime"]
    pct = 100.0 if total_time.total_seconds() == 0 else (total_up / total_time * 100)
    return {
        "current": str(current),
        "total_uptime": str(total_up),
        "total_downtime": str(state["total_downtime"]),
        "uptime_pct": f"{pct:.1f}%",
        "last_start": state["last_start"].isoformat() if state["last_start"] else "never",
        "last_end": state["last_end"].isoformat() if state["last_end"] else "never"
    }

init_db()