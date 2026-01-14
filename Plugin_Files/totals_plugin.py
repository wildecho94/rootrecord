# Plugin_Files/totals_plugin.py
# Version: 1.42.20260114 – Absolute totals updater

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add rootrecord/ to path

import sqlite3
import json
import time
import threading
from datetime import datetime

from utils.config_manager import load_config

config = load_config()
ROOT = Path(config["root_folder"])
DB_PATH = ROOT / config["master_db"]
TOTALS_JSON = ROOT / "web" / "totals.json"

def init_tables():
    """Create missing tables if they don't exist (minimal schema)"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # pings (example minimal)
        c.execute('''
            CREATE TABLE IF NOT EXISTS pings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TEXT
            )
        ''')
        # vehicles
        c.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plate TEXT
            )
        ''')
        # fuel_records
        c.execute('''
            CREATE TABLE IF NOT EXISTS fuel_records (
                fill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER
            )
        ''')
        # finance_records
        c.execute('''
            CREATE TABLE IF NOT EXISTS finance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER
            )
        ''')
        # activity_sessions
        c.execute('''
            CREATE TABLE IF NOT EXISTS activity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER
            )
        ''')
        conn.commit()
    print("[totals_plugin] Checked/created missing tables")

def calculate_totals():
    init_tables()  # Ensure tables exist before counting

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

        try:
            c.execute("SELECT COUNT(DISTINCT user_id) FROM pings")
            totals["users"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] pings table missing/skipped: {e}")

        try:
            c.execute("SELECT COUNT(*) FROM pings")
            totals["pings"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] pings table missing/skipped: {e}")

        try:
            c.execute("SELECT COUNT(*) FROM vehicles")
            totals["vehicles"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] vehicles table missing/skipped: {e}")

        try:
            c.execute("SELECT COUNT(*) FROM fuel_records")
            totals["fillups"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] fuel_records table missing/skipped: {e}")

        try:
            c.execute("SELECT COUNT(*) FROM finance_records")
            totals["finance_entries"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] finance_records table missing/skipped: {e}")

        try:
            c.execute("SELECT COUNT(*) FROM activity_sessions")
            totals["activities"] = c.fetchone()[0] or 0
        except sqlite3.OperationalError as e:
            print(f"[totals_plugin] activity_sessions table missing/skipped: {e}")

    # Write to JSON
    with open(TOTALS_JSON, "w", encoding="utf-8") as f:
        json.dump(totals, f, indent=2)

    print(f"[totals_plugin] Totals updated: {totals}")
    return totals

def totals_loop():
    while True:
        try:
            calculate_totals()
        except Exception as e:
            print(f"[totals_plugin] Loop error: {e}")
        time.sleep(60)

def initialize():
    thread = threading.Thread(target=totals_loop, daemon=True, name="TotalsUpdater")
    thread.start()
    print("[totals_plugin] Initialized – updating totals every 60s")