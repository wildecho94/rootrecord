# Plugin_Files/a_gps_plugin.py
# Edited Version: 1.42.20260112 (updated for early loading + self-wait)

"""
GPS Tracker plugin - main entry point
Loads early and waits for Telegram app to be ready
"""

import time
from Core_Files.gps_tracker_core import init_db
from Handler_Files.gps_tracker_handler import register_gps_handler

# Direct import of the global app from telegram_plugin
try:
    from Plugin_Files.telegram_plugin import app as telegram_app
except ImportError:
    telegram_app = None

def initialize():
    """
    Initialize DB and wait for Telegram app to become available.
    Since this plugin loads early (a_gps_plugin), we actively poll for app.
    """
    init_db()
    print("[a_gps_plugin] DB initialized - waiting for Telegram app...")

    # Wait for telegram_app to be set (Telegram plugin runs in background thread)
    max_wait_seconds = 45
    waited = 0
    step = 1.0  # check every second

    while telegram_app is None and waited < max_wait_seconds:
        print(f"[a_gps_plugin] Telegram app not ready yet... waited {waited}s / {max_wait_seconds}s")
        time.sleep(step)
        waited += step

        # Re-import in case it was set after initial import
        try:
            from Plugin_Files.telegram_plugin import app as telegram_app_ref
            if telegram_app_ref is not None:
                telegram_app = telegram_app_ref
                break
        except ImportError:
            pass

    if telegram_app is not None:
        print("[a_gps_plugin] Telegram app found! Registering GPS handlers...")
        register_gps_handler(telegram_app)
        print("[a_gps_plugin] Handlers registered - tracking active")
    else:
        print(f"[a_gps_plugin] ERROR: Telegram app never became available after {max_wait_seconds} seconds")
        print("[a_gps_plugin] GPS tracking will NOT work until Telegram plugin finishes startup")

# Optional: if you still want to keep late_register as fallback (not needed now)
def late_register(telegram_app):
    if telegram_app is None:
        print("[a_gps_plugin] ERROR: received None app in late_register")
        return
    
    register_gps_handler(telegram_app)
    print("[a_gps_plugin] Handlers registered via late_register - tracking active")