# Plugin_Files/telegram.py
"""
Telegram plugin — config, DB helpers, connection filtering
Auto-creates config_telegram.json in root directory
"""

PLUGIN_NAME = "telegram"
PLUGIN_PRIORITY = 10
PLUGIN_VERSION = "0.1"
PLUGIN_DESCRIPTION = "Telegram bot with DM/group/channel/topic support"

from pathlib import Path
import json
import sqlite3
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config_telegram.json"
DATA_FOLDER = BASE_DIR / "data"
DATABASE = DATA_FOLDER / "rootrecord.db"


DEFAULT_CONFIG = {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "enabled": True,
    "default_parse_mode": "HTML",
    "connections": {
        "dm": {
            "enabled": False,
            "allowed_users": []  # [123456789, ...]
        },
        "groups": {
            "enabled": False,
            "chat_ids": []  # [-1001234567890, ...]
        },
        "supergroups": {
            "enabled": False,
            "chat_ids": [],
            "topics": {}  # {"-1001234567890": [1, 2, 3]}
        },
        "channels": {
            "enabled": False,
            "chat_ids": []  # [-1001112223334]
        }
    }
}


def create_default_config():
    if CONFIG_PATH.exists():
        return

    print(f"[{PLUGIN_NAME}] Creating default config: {CONFIG_PATH}")
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
    print(f"[{PLUGIN_NAME}] Config created. Edit bot_token and enable connections!")


def load_config():
    create_default_config()
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[{PLUGIN_NAME}] Config load failed, using defaults: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        print(f"[{PLUGIN_NAME}] Config saved")
    except Exception as e:
        print(f"[{PLUGIN_NAME}] Save failed: {e}")


def ensure_users_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def register_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()
    print(f"[{PLUGIN_NAME}] Registered/updated user: {user_id} ({username or 'no username'})")


def initialize():
    config = load_config()
    ensure_users_table()

    token_ok = not config["bot_token"].startswith("YOUR_")
    print(f"[{PLUGIN_NAME}] Token: {'VALID' if token_ok else 'MISSING'}")

    enabled = [k for k, v in config["connections"].items() if v["enabled"]]
    print(f"[{PLUGIN_NAME}] Enabled connections: {', '.join(enabled) or 'none'}")

    if token_ok:
        print(f"[{PLUGIN_NAME}] Ready for bot polling (handled in core file)")
    else:
        print(f"[{PLUGIN_NAME}] Edit {CONFIG_PATH} and restart")


if __name__ == "__main__":
    initialize()