# Plugin_Files/gps_plugin.py
# Edited Version: 1.42.20260112 (fixed)

"""
GPS Tracker plugin - main entry point
"""

from Core_Files.gps_tracker_core import init_db
from Handler_Files.gps_tracker_handler import register_gps_handler

def initialize():
    init_db()
    print("[gps_plugin] DB initialized - waiting for late registration...")

def late_register(telegram_app):
    if telegram_app is None:
        print("[gps_plugin] ERROR: received None app in late_register")
        return
    
    register_gps_handler(telegram_app)
    print("[gps_plugin] Handlers registered - tracking active")