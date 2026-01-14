# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – DB-based totals updater (no JSON file)

import sqlite3
import threading
import time
from datetime import datetime

# Hardcoded DB path (since no utils/config yet)
DB_PATH = "C:/Users/Alexrs94/Desktop/programfiles/rootrecord/data/rootrecord.db"

def create_totals_table():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_totals (
                id INTEGER PRIMARY KEY CHECK (id = 1),  -- single row only
                total_users INTEGER DEFAULT 0,
                total_pings INTEGER DEFAULT 0,
                total_vehicles INTEGER DEFAULT 0,
                total_fillups INTEGER DEFAULT 0,
                total_finance_entries INTEGER DEFAULT 0,
                total_activities INTEGER DEFAULT 0,
                updated_at TEXT
            )
        ''')
        # Insert default row if missing
        c.execute("INSERT OR IGNORE INTO dashboard_totals (id) VALUES (1)")
        conn.commit()
    print("[totals_plugin] dashboard_totals table ready")

def update_totals():
    totals = {
        "total_users": 0,
        "total_pings": 0,
        "total_vehicles": 0,
        "total_fillups": 0,
        "total_finance_entries": 0,
        "total_activities": 0,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    with sqlite3.connect(DB_PATH) as conn:
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

        # Update single row
        c.execute('''
            UPDATE dashboard_totals SET
                total_users = ?,
                total_pings = ?,
                total_vehicles = ?,
                total_fillups = ?,
                total_finance_entries = ?,
                total_activities = ?,
                updated_at = ?
            WHERE id = 1
        ''', (
            totals["total_users"],
            totals["total_pings"],
            totals["total_vehicles"],
            totals["total_fillups"],
            totals["total_finance_entries"],
            totals["total_activities"],
            totals["updated_at"]
        ))
        conn.commit()

    print(f"[totals_plugin] DB totals updated: {totals}")

def totals_loop():
    while True:
        try:
            update_totals()
        except Exception as e:
            print(f"[totals_plugin] Update error: {e}")
        time.sleep(60)

def initialize():
    create_totals_table()
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – updating DB totals every 60s")