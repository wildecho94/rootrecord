# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – Absolute totals updater

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

def calculate_totals():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Total unique users
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
        total_finance = c.fetchone()[0] or 0

        # Total activities
        c.execute("SELECT COUNT(*) FROM activity_sessions")
        total_activities = c.fetchone()[0] or 0

    totals = {
        "users": total_users,
        "pings": total_pings,
        "vehicles": total_vehicles,
        "fillups": total_fillups,
        "finance_entries": total_finance,
        "activities": total_activities,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Write to JSON for index.html
    with open(TOTALS_JSON, "w", encoding="utf-8") as f:
        json.dump(totals, f, indent=2)

    print(f"[totals_plugin] Totals updated: {totals}")

def totals_loop():
    while True:
        try:
            calculate_totals()
        except Exception as e:
            print(f"[totals_plugin] Error: {e}")
        time.sleep(60)  # every minute

def initialize():
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – updating totals every 60s")