# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – Calculates and caches absolute totals

import sqlite3
import json
import time
import threading
from pathlib import Path
from datetime import datetime

from utils.config_manager import load_config

config = load_config()
ROOT = Path(config["root_folder"])
DB_PATH = ROOT / config["master_db"]
TOTALS_JSON = ROOT / "web" / "totals.json"
TOTALS_TABLE = "totals_history"

def init_totals_table():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS totals_history (
                timestamp TEXT PRIMARY KEY,
                total_users INTEGER,
                total_pings INTEGER,
                total_vehicles INTEGER,
                total_fillups INTEGER,
                total_finance_entries INTEGER,
                total_activities INTEGER
            )
        ''')
        conn.commit()
    print("[totals_plugin] totals_history table ready")

def calculate_totals():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Total unique users (from pings or users table)
        c.execute("SELECT COUNT(DISTINCT user_id) FROM pings")
        total_users = c.fetchone()[0] or 0

        # Total pings
        c.execute("SELECT COUNT(*) FROM pings")
        total_pings = c.fetchone()[0] or 0

        # Total vehicles
        c.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = c.fetchone()[0] or 0

        # Total fill-ups
        c.execute("SELECT COUNT(*) FROM fuel_records")
        total_fillups = c.fetchone()[0] or 0

        # Total finance entries
        c.execute("SELECT COUNT(*) FROM finance_records")
        total_finance_entries = c.fetchone()[0] or 0

        # Total activities (sessions)
        c.execute("SELECT COUNT(*) FROM activity_sessions")
        total_activities = c.fetchone()[0] or 0

    totals = {
        "users": total_users,
        "pings": total_pings,
        "vehicles": total_vehicles,
        "fillups": total_fillups,
        "finance_entries": total_finance_entries,
        "activities": total_activities,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Save to JSON
    with open(TOTALS_JSON, "w", encoding="utf-8") as f:
        json.dump(totals, f, indent=2)

    # Save to DB history
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO totals_history 
            (timestamp, total_users, total_pings, total_vehicles, total_fillups, total_finance_entries, total_activities)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (totals["updated_at"], total_users, total_pings, total_vehicles, total_fillups, total_finance_entries, total_activities))
        conn.commit()

    print(f"[totals_plugin] Totals updated: {totals}")
    return totals

def totals_loop():
    while True:
        try:
            calculate_totals()
        except Exception as e:
            print(f"[totals_plugin] Error calculating totals: {e}")
        time.sleep(60)  # every minute

def initialize():
    init_totals_table()
    # Start background thread
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – totals updating every 60s")