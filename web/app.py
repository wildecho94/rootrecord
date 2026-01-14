# rootrecord/web/app.py
# v1.42.20260114 – Serves index.html + totals.json

from flask import Flask, send_from_directory, jsonify
import json
from pathlib import Path

app = Flask(__name__, static_folder='.')

TOTALS_JSON = Path("totals.json")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/totals.json')
def totals():
    try:
        with open(TOTALS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Totals not ready"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)