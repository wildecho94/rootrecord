# RootRecord Plugin_Files/gps_tracker.py
# Edited Version: 1.42.20260111

"""
GPS Tracker plugin - main entry point

Listens for shared locations in Telegram, processes via core, stores in DB.
"""

from Core_Files.gps_tracker_core import init_db, process_location
from Handler_Files.gps_tracker_handler import register_gps_handler

def initialize():
    init_db()
    register_gps_handler()
    print("[gps_tracker] Initialized and ready to track shared locations")