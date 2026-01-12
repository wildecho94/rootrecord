# Plugin_Files/gps_tracker.py
# Edited Version: 1.42.20260112

"""
GPS Tracker plugin - main entry point
"""

from Core_Files.gps_tracker_core import init_db
from Handler_Files.gps_tracker_handler import register_gps_handler

def initialize():
    init_db()
    # Access global app from telegram_plugin (assuming exposed as global 'app')
    from Plugin_Files.telegram_plugin import app as telegram_app
    register_gps_handler(telegram_app)
    print("[gps_tracker] Initialized and ready to track shared/edited locations")