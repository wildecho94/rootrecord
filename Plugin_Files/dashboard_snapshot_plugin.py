# Plugin_Files/dashboard_snapshot_plugin.py
# Version: 20260118-fix5 – Fixed datetime import, added missing import traceback, safe fallback

"""
Dashboard Snapshot Plugin – Automates updates to dashboard_totals table
Runs every 10 minutes in background async loop
"""

import asyncio
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import traceback

# Import datetime safely
try:
    from datetime import datetime
except ImportError as ie:
    print(f"[dashboard_snapshot] CRITICAL: datetime import failed: {ie}")
    raise

from utils.db_mysql import config  # Shared config loader

ROOT = Path(__file__).parent.parent

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
                0
        """)
        conn.commit()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[dashboard_snapshot] Totals updated at {now_str}")

    except Error as e:
        print(f"[dashboard_snapshot] MySQL error: {e}")
    except Exception as e:
        print(f"[dashboard_snapshot] Unexpected error: {type(e).__name__}: {e}")
        print(traceback.format_exc())
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

async def periodic_update():
    print("[dashboard_snapshot] Starting periodic updates (every 10 min)")
    while True:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, update_snapshot)
        await asyncio.sleep(600)

def initialize():
    print("[dashboard_snapshot] Initializing...")
    # Ensure table exists
    conn = None
    cursor = None
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
        print(f"[dashboard_snapshot] Table setup failed: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    # Start updater
    asyncio.create_task(periodic_update())
    print("[dashboard_snapshot] Initialized – 10-min snapshot updates active")