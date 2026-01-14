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
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM dashboard_totals_history ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            if row:
                return jsonify({
                    "users": row[2],          # total_users
                    "pings": row[3],
                    "vehicles": row[4],
                    "fillups": row[5],
                    "finance_entries": row[6],
                    "activities": row[7],
                    "updated_at": row[1]      # timestamp
                })
            else:
                return jsonify({"error": "No totals data yet"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500