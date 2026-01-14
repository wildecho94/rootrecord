# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – Absolute totals updater

import sqlite3
import json
import time
import threading
from pathlib import Path
from datetime import datetime

# Hardcoded paths (no utils dependency)
ROOT = Path("C:/Users/Alexrs94/Desktop/programfiles/rootrecord")
DB_PATH = ROOT / "data" / "rootrecord.db"
TOTALS_JSON = ROOT / "web" / "totals.json"

def create_missing_tables():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Minimal schema for counting
        c.execute('''
            CREATE TABLE IF NOT EXISTS pings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                fill_id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS activity_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        conn.commit()
    print("[totals_plugin] Checked/created missing tables")

def calculate_totals():
    create_missing_tables()  # Ensure tables exist

    totals = {
        "users": 0,
        "pings": 0,
        "vehicles": 0,
        "fillups": 0,
        "finance_entries": 0,
        "activities": 0,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        try: c.execute("SELECT COUNT(DISTINCT user_id) FROM pings"); totals["users"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] pings users error: {e}")

        try: c.execute("SELECT COUNT(*) FROM pings"); totals["pings"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] pings count error: {e}")

        try: c.execute("SELECT COUNT(*) FROM vehicles"); totals["vehicles"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] vehicles error: {e}")

        try: c.execute("SELECT COUNT(*) FROM fuel_records"); totals["fillups"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] fillups error: {e}")

        try: c.execute("SELECT COUNT(*) FROM finance_records"); totals["finance_entries"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] finance error: {e}")

        try: c.execute("SELECT COUNT(*) FROM activity_sessions"); totals["activities"] = c.fetchone()[0] or 0
        except Exception as e: print(f"[totals] activities error: {e}")

    try:
        with open(TOTALS_JSON, "w", encoding="utf-8") as f:
            json.dump(totals, f, indent=2)
        print(f"[totals_plugin] totals.json updated: {totals}")
    except Exception as e:
        print(f"[totals_plugin] Failed to write totals.json: {e}")

def totals_loop():
    while True:
        calculate_totals()
        time.sleep(60)

def initialize():
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – updating totals every 60s")