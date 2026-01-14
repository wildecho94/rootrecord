# rootrecord/web/app.py
# RootRecord Web Dashboard – v1.42.20260114

from flask import Flask, send_from_directory, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Path to master DB (adjust if needed)
DB_PATH = Path(__file__).parent.parent / "data" / "rootrecord.db"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/server_stats.json')
def server_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Total users (distinct user_id in pings)
        c.execute("SELECT COUNT(DISTINCT user_id) as users FROM pings")
        users = c.fetchone()[0] or 0

        # Total pings
        c.execute("SELECT COUNT(*) as pings FROM pings")
        pings = c.fetchone()[0] or 0

        # Total activities (sessions)
        c.execute("SELECT COUNT(*) as activities FROM activity_sessions")
        activities = c.fetchone()[0] or 0

        # Uptime (simple example: time since last bot start, replace with real uptime logic if needed)
        uptime = "Running since " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.close()

        return jsonify({
            "users": users,
            "pings": pings,
            "uptime": uptime,
            "activities": activities
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)