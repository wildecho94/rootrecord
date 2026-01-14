# rootrecord/web/app.py
# RootRecord Web Dashboard – v1.42.20260114
# Serves index.html + live totals from DB (no JSON files)

from flask import Flask, send_from_directory, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__, static_folder='.')

# Paths
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/totals.json')
def totals():
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

            # Safe counts – skip if table missing
            try:
                c.execute("SELECT COUNT(DISTINCT user_id) FROM pings")
                totals["users"] = c.fetchone()[0] or 0
            except sqlite3.OperationalError:
                pass

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

        return jsonify(totals)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)