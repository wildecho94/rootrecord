# rootrecord/web/app.py
# RootRecord Web Dashboard – v1.42.20260114
# Serves index.html + totals.json with real DB totals

from flask import Flask, send_from_directory, jsonify
import sqlite3
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__, static_folder='.')

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"
TOTALS_JSON = Path("totals.json")  # rootrecord/totals.json

def calculate_totals():
    totals = {
        "users": 0,
        "pings": 0,
        "vehicles": 0,
        "fillups": 0,
        "finance_entries": 0,
        "activities": 0,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            try:
                c.execute("SELECT COUNT(DISTINCT user_id) FROM pings")
                totals["users"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass  # table missing → keep 0

            try:
                c.execute("SELECT COUNT(*) FROM pings")
                totals["pings"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("SELECT COUNT(*) FROM vehicles")
                totals["vehicles"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("SELECT COUNT(*) FROM fuel_records")
                totals["fillups"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("SELECT COUNT(*) FROM finance_records")
                totals["finance_entries"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("SELECT COUNT(*) FROM activity_sessions")
                totals["activities"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

        # Write to JSON
        with open(TOTALS_JSON, "w", encoding="utf-8") as f:
            json.dump(totals, f, indent=2)

        print(f"[app] Totals updated: {totals}")
        return totals
    except Exception as e:
        print(f"[app] Error calculating totals: {e}")
        return totals  # return zeros on failure

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/totals.json')
def totals():
    if not TOTALS_JSON.exists():
        print("[app] totals.json not found – generating now")
        return jsonify(calculate_totals())

    try:
        with open(TOTALS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"[app] Error reading totals.json: {e} – regenerating")
        return jsonify(calculate_totals())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)