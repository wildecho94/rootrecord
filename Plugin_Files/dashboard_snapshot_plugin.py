# Plugin_Files/dashboard_snapshot_plugin.py
# Version: 1.42.20260117 – Full file with improved timestamped logging for visibility
#          Every update now prints success/failure clearly in console

import asyncio
import mysql.connector
from mysql.connector import Error
from datetime import datetime

from utils.db_mysql import config
from pathlib import Path

ROOT = Path(__file__).parent.parent

def update_snapshot():
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=config["mysql_user"],
            password=config["mysql_password"],
            database=config["mysql_db"],
            connect_timeout=10,
            raise_on_warnings=True
        )
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO dashboard_totals (
                total_users, total_pings, total_vehicles, total_fillups,
                total_finance_entries, total_activities
            )
            SELECT 
                (SELECT COUNT(DISTINCT user_id) FROM gps_records) AS total_users,
                (SELECT COUNT(*) FROM gps_records) AS total_pings,
                (SELECT COUNT(*) FROM vehicles) AS total_vehicles,
                (SELECT COUNT(*) FROM fuel_records) AS total_fillups,
                (SELECT COUNT(*) FROM finance_records) AS total_finance_entries,
                0 AS total_activities
        """)
        conn.commit()
        print(f"[{now_str}] [dashboard_snapshot] Totals updated successfully")

    except Error as e:
        print(f"[{now_str}] [dashboard_snapshot] MySQL error during update: {e}")
    except Exception as e:
        print(f"[{now_str}] [dashboard_snapshot] Unexpected error during update: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

async def periodic_update():
    print("[dashboard_snapshot] Starting periodic updates (every 10 minutes)")
    while True:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, update_snapshot)
        await asyncio.sleep(600)  # 10 minutes

def initialize():
    print("[dashboard_snapshot] Initializing dashboard_totals table...")
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

    asyncio.create_task(periodic_update())
    print("[dashboard_snapshot] Initialized – running updates every 10 minutes")