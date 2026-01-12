# Plugin_Files/gps_plugin.py
# Edited Version: 1.42.20260112

"""
GPS Tracker plugin - main entry point
"""

from Core_Files.gps_tracker_core import init_db
from Handler_Files.gps_tracker_handler import register_gps_handler
import time

def initialize():
    init_db()
    print("[gps_plugin] DB initialized - waiting for telegram app...")

def late_register():
    from Plugin_Files.telegram_plugin import app as telegram_app
    # Retry briefly in case of very tight timing
    for attempt in range(10):
        if telegram_app is not None:
            register_gps_handler(telegram_app)
            print("[gps_plugin] Handlers registered - tracking active")
            return
        print(f"[gps_plugin] Waiting for telegram app... (attempt {attempt+1}/10)")
        time.sleep(0.5)
    print("[gps_plugin] ERROR: telegram app never became available")