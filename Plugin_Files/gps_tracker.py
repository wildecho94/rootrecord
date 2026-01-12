# Plugin_Files/gps_tracker.py
# Edited Version: 1.42.20260112

"""
GPS Tracker plugin - main entry point
"""

from Core_Files.gps_tracker_core import init_db
from Handler_Files.gps_tracker_handler import register_gps_handler

def initialize():
    init_db()
    print("[gps_tracker] DB initialized - waiting for telegram app...")

def late_register():
    from Plugin_Files.telegram_plugin import app as telegram_app
    if telegram_app is None:
        print("[gps_tracker] ERROR: telegram app still None")
        return
    register_gps_handler(telegram_app)
    print("[gps_tracker] Handlers registered - tracking active")