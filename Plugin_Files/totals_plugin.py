# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – Periodic totals saved to dashboard_totals_history table

import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

def table_exists(table_name):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return c.fetchone() is not None

def create_totals_history_table():
    if table_exists("dashboard_totals_history"):
        print("[totals_plugin] dashboard_totals_history table already exists – skipping creation")
    else:
        print("[totals_plugin] Creating dashboard_totals_history table...")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE dashboard_totals_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_users INTEGER DEFAULT 0,
                    total_pings INTEGER DEFAULT 0,
                    total_vehicles INTEGER DEFAULT 0,
                    total_fillups INTEGER DEFAULT 0,
                    total_finance_entries INTEGER DEFAULT 0,
                    total_activities INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'periodic',
                    notes TEXT
                )
            ''')
            conn.commit()
    print("[totals_plugin] dashboard_totals_history table ready")

def save_totals_to_db(totals):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO dashboard_totals_history (
                timestamp, total_users, total_pings, total_vehicles,
                total_fillups, total_finance_entries, total_activities,
                source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            totals["total_users"],
            totals["total_pings"],
            totals["total_vehicles"],
            totals["total_fillups"],
            totals["total_finance_entries"],
            totals["total_activities"],
            "periodic",
            None
        ))
        conn.commit()
    print(f"[totals_plugin] Saved snapshot at {timestamp}")

def calculate_and_save_totals():
    totals = {
        "total_users": 0,
        "total_pings": 0,
        "total_vehicles": 0,
        "total_fillups": 0,
        "total_finance_entries": 0,
        "total_activities": 0
    }

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()

        try: c.execute("SELECT COUNT(DISTINCT user_id) FROM pings"); totals["total_users"] = c.fetchone()[0] or 0
        except: pass

        try: c.execute("SELECT COUNT(*) FROM pings"); totals["total_pings"] = c.fetchone()[0] or 0
        except: pass

        try: c.execute("SELECT COUNT(*) FROM vehicles"); totals["total_vehicles"] = c.fetchone()[0] or 0
        except: pass

        try: c.execute("SELECT COUNT(*) FROM fuel_records"); totals["total_fillups"] = c.fetchone()[0] or 0
        except: pass

        try: c.execute("SELECT COUNT(*) FROM finance_records"); totals["total_finance_entries"] = c.fetchone()[0] or 0
        except: pass

        try: c.execute("SELECT COUNT(*) FROM activity_sessions"); totals["total_activities"] = c.fetchone()[0] or 0
        except: pass

    save_totals_to_db(totals)
    return totals

def totals_loop():
    while True:
        try:
            calculate_and_save_totals()
        except Exception as e:
            print(f"[totals_plugin] Loop error: {e}")
        time.sleep(60)

def initialize():
    create_totals_history_table()
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – saving totals to DB every 60s")