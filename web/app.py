# rootrecord/web/app.py
# RootRecord Web Dashboard – v1.42.20260114

from flask import Flask, send_from_directory, jsonify
import json
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__, static_folder='.')

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"
TOTALS_JSON = Path("totals.json")  # rootrecord/totals.json

def calculate_totals():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            c.execute("SELECT COUNT(DISTINCT user_id) FROM pings")
            total_users = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM pings")
            total_pings = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM vehicles")
            total_vehicles = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM fuel_records")
            total_fillups = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM finance_records")
            total_finance = c.fetchone()[0] or 0

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

        # Create/write JSON
        with open(TOTALS_JSON, "w", encoding="utf-8") as f:
            json.dump(totals, f, indent=2)

        print(f"[app] Created/updated totals.json: {totals}")
        return totals
    except Exception as e:
        print(f"[app] Error calculating totals: {e}")
        return {"error": str(e)}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/totals.json')
def totals():
    if not TOTALS_JSON.exists():
        # Create on first request if missing
        print("[app] totals.json not found – generating now")
        return jsonify(calculate_totals())

    try:
        with open(TOTALS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        # Regenerate if corrupted
        print(f"[app] Error reading totals.json: {e} – regenerating")
        return jsonify(calculate_totals())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)