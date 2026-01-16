# Plugin_Files/dashboard_snapshot_plugin.py
# Version: 20260118 – Periodic snapshot updater for dashboard_totals (MySQL)

"""
Dashboard Snapshot Plugin – Automates updates to dashboard_totals table
Runs every 10 minutes (600s) in background async loop
Uses sync MySQL connector for simplicity (non-blocking via executor)
"""

import asyncio
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import json

from utils.db_mysql import config  # Reuse shared config (mysql_user, etc.)

ROOT = Path(__file__).parent.parent

# ────────────────────────────────────────────────
# Update function (sync for mysql.connector)
# ────────────────────────────────────────────────
def update_snapshot():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=config["mysql_user"],
            password=config["mysql_password"],
            database=config["mysql_db"],
            connect_timeout=10
        )
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO dashboard_totals (
                total_users, total_pings, total_vehicles, total_fillups,
                total_finance_entries, total_activities
            )
            SELECT 
                (SELECT COUNT(DISTINCT user_id) FROM gps_records),
                (SELECT COUNT(*) FROM gps_records),
                (SELECT COUNT(*) FROM vehicles),
                (SELECT COUNT(*) FROM fuel_records),
                (SELECT COUNT(*) FROM finance_records),
                0  -- activities placeholder; replace with real query if table exists
        """)
        conn.commit()
        print("[dashboard_snapshot] Totals updated successfully at " + str(datetime.now()))

    except Error as e:
        print(f"[dashboard_snapshot] MySQL error during update: {e}")

    except Exception as e:
        print(f"[dashboard_snapshot] Unexpected error: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# ────────────────────────────────────────────────
# Async periodic runner
# ────────────────────────────────────────────────
async def periodic_update():
    print("[dashboard_snapshot] Starting periodic updates (every 10 minutes)")
    while True:
        # Run sync DB operation in executor so it doesn't block the asyncio loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, update_snapshot)
        await asyncio.sleep(60)  # 600 seconds = 10 minutes

# ────────────────────────────────────────────────
# Plugin entry point
# ────────────────────────────────────────────────
def initialize():
    # Ensure table exists (safe to run multiple times)
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=config["mysql_user"],
            password=config["mysql_password"],
            database=config["mysql_db"]
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_totals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                total_users INT DEFAULT 0,
                total_pings INT DEFAULT 0,
                total_vehicles INT DEFAULT 0,
                total_fillups INT DEFAULT 0,
                total_finance_entries INT DEFAULT 0,
                total_activities INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        print("[dashboard_snapshot] Ensured dashboard_totals table exists")
    except Exception as e:
        print(f"[dashboard_snapshot] Table creation/check failed: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Start the background updater
    asyncio.create_task(periodic_update())
    print("[dashboard_snapshot] Initialized – running 10-min updates for dashboard_totals")