# rootrecord/web/app.py
# RootRecord Web Dashboard – v1.45.20260118
# Uses dashboard_totals snapshot table (primary) + live fallback; MySQL only

from flask import Flask, send_from_directory, jsonify
from pathlib import Path
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__, static_folder='.')

# Paths
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config_mysql.json"

# Load MySQL config (shared across project)
def load_mysql_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing {CONFIG_PATH} – create it with mysql_user, mysql_password, mysql_db")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    required = ["mysql_user", "mysql_password", "mysql_db"]
    for key in required:
        if key not in config or not config[key]:
            raise ValueError(f"Missing or empty '{key}' in config_mysql.json")
    return config

config = load_mysql_config()

def get_mysql_connection():
    return mysql.connector.connect(
        host="localhost",
        user=config["mysql_user"],
        password=config["mysql_password"],
        database=config["mysql_db"],
        raise_on_warnings=True,
        connect_timeout=10
    )

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/totals.json')
def totals():
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        # Primary: Get the most recent snapshot from dashboard_totals
        cursor.execute("""
            SELECT 
                total_users,
                total_pings,
                total_vehicles,
                total_fillups,
                total_finance_entries,
                total_activities,
                updated_at
            FROM dashboard_totals
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if row:
            return jsonify({
                "users": row.get("total_users", 0),
                "pings": row.get("total_pings", 0),
                "vehicles": row.get("total_vehicles", 0),
                "fillups": row.get("total_fillups", 0),
                "finance_entries": row.get("total_finance_entries", 0),
                "activities": row.get("total_activities", 0),
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else datetime.utcnow().isoformat(),
                "source": "snapshot"
            })

        # Fallback: No snapshot yet → compute live aggregates
        print("[dashboard] No snapshot found → falling back to live counts")
        cursor.execute("""
            SELECT 
                (SELECT COUNT(DISTINCT user_id) FROM gps_records) AS total_users,
                (SELECT COUNT(*) FROM gps_records) AS total_pings,
                (SELECT COUNT(*) FROM vehicles) AS total_vehicles,
                (SELECT COUNT(*) FROM fuel_records) AS total_fillups,
                (SELECT COUNT(*) FROM finance_records) AS total_finance_entries,
                0 AS total_activities,
                NOW() AS updated_at
        """)
        fallback = cursor.fetchone()

        if fallback:
            return jsonify({
                "users": fallback.get("total_users", 0),
                "pings": fallback.get("total_pings", 0),
                "vehicles": fallback.get("total_vehicles", 0),
                "fillups": fallback.get("total_fillups", 0),
                "finance_entries": fallback.get("total_finance_entries", 0),
                "activities": fallback.get("total_activities", 0),
                "updated_at": fallback["updated_at"].isoformat() if fallback["updated_at"] else datetime.utcnow().isoformat(),
                "source": "live_fallback",
                "note": "snapshot table empty – consider running update task"
            })

        return jsonify({"error": "No data available in database"}), 503

    except Error as e:
        print(f"[dashboard] MySQL error: {e}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        print(f"[dashboard] Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    print("[dashboard] Starting Flask server (MySQL snapshot + fallback mode) – http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)