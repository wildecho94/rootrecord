# RootRecord Core_Files/gps_tracker_core.py
# Edited Version: 1.42.20260112

"""
GPS Tracker core logic - full location processing, geocoding, zone detection,
activity tracking, stats update, and storage of all received/derived data.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from plugins.gps.geofencing import determine_zone, check_geofence_change
from plugins.activities.rideshare.state_rideshare import (
    is_activity_active,
    load_activity_state,
    save_activity_state
)
from plugins.activities.rideshare.handler_rideshare import get_activity_display
from utils.calculator import update_calculated_stats
from utils.helpers import ensure_user_folder, safe_json_read, safe_json_write

DB_PATH = Path(__file__).parent.parent / "data" / "rootrecord.db"
geolocator = Nominatim(user_agent="rootrecord_gps_tracker")

def init_db():
    """Initialize gps_records table with all possible fields from old system."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                message_id INTEGER,
                timestamp TEXT NOT NULL,
                edit_timestamp TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                heading REAL,
                horizontal_accuracy REAL,
                live_period INTEGER,
                address TEXT,
                city TEXT,
                country TEXT,
                postal_code TEXT,
                neighborhood TEXT,
                zone TEXT,
                zone_changed INTEGER DEFAULT 0,
                raw_geopy_data TEXT,
                full_record_text TEXT
            )
        ''')
        conn.commit()

def process_location(update):
    """Process new or edited location message, store all data, update stats/activity."""
    msg = update.message or update.edited_message
    if not msg or not msg.location:
        return

    user = msg.from_user
    loc = msg.location

    user_id = user.id
    username = user.username or "[no username]"
    first_name = user.first_name or "[no name]"
    last_name = user.last_name or ""
    message_id = msg.message_id
    timestamp = datetime.fromtimestamp(msg.date).isoformat() if msg.date else datetime.utcnow().isoformat()
    edit_timestamp = datetime.fromtimestamp(msg.edit_date).isoformat() if msg.edit_date else None
    latitude = loc.latitude
    longitude = loc.longitude
    heading = loc.heading if hasattr(loc, 'heading') else None
    horizontal_accuracy = loc.horizontal_accuracy if hasattr(loc, 'horizontal_accuracy') else None
    live_period = loc.live_period if hasattr(loc, 'live_period') else None

    # Geocoding
    address = city = country = postal = neighborhood = raw_data = None
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True, timeout=10)
        if location:
            raw_data = json.dumps(location.raw, default=str)
            address = location.address
            addr_dict = location.raw.get('address', {})
            city = addr_dict.get('city') or addr_dict.get('town') or addr_dict.get('village')
            country = addr_dict.get('country')
            postal = addr_dict.get('postcode')
            neighborhood = addr_dict.get('neighbourhood') or addr_dict.get('suburb')
    except (GeocoderTimedOut, GeocoderUnavailable):
        print("[gps_tracker_core] Geocoding timeout/unavailable")
    except Exception as e:
        print(f"[gps_tracker_core] Geocoding error: {e}")

    # Zone detection & change check (from old geofencing)
    zone = determine_zone(user_id, latitude, longitude)
    zone_changed = 0
    # Check if zone changed (requires previous location - placeholder logic)
    # For simplicity, we assume zone change is detected in geofencing module
    if check_geofence_change(user_id, latitude, longitude, latitude, longitude):  # prev coords needed in real impl
        zone_changed = 1

    # Build readable one-line summary (all data)
    edit_note = f" (edited at {edit_timestamp})" if edit_timestamp else ""
    heading_note = f" | Heading: {heading}°" if heading else ""
    accuracy_note = f" | Acc: ±{horizontal_accuracy}m" if horizontal_accuracy else ""
    live_note = f" | Live: {live_period}s" if live_period else ""
    readable = (
        f"User: {first_name} {last_name} (@{username}, id:{user_id}) | "
        f"Msg ID: {message_id}{edit_note} | Time: {timestamp} | "
        f"Location: {latitude:.6f}, {longitude:.6f}{heading_note}{accuracy_note}{live_note} | "
        f"Zone: {zone} (changed: {'Yes' if zone_changed else 'No'}) | "
        f"Address: {address or 'N/A'} | City: {city or 'N/A'} | "
        f"Country: {country or 'N/A'} | Postal: {postal or 'N/A'} | "
        f"Neighborhood: {neighborhood or 'N/A'}"
    )
    print(readable)

    # Store EVERYTHING in DB
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO gps_records 
            (user_id, username, first_name, last_name, message_id, timestamp, edit_timestamp,
             latitude, longitude, heading, horizontal_accuracy, live_period,
             address, city, country, postal_code, neighborhood, zone, zone_changed,
             raw_geopy_data, full_record_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, first_name, last_name, message_id, timestamp, edit_timestamp,
            latitude, longitude, heading, horizontal_accuracy, live_period,
            address, city, country, postal, neighborhood, zone, zone_changed,
            raw_data, readable
        ))
        conn.commit()

    print("[gps_tracker_core] Location fully stored")

    # Update user stats & activity (from old system)
    update_calculated_stats(user_id)

    if is_activity_active(user_id):
        state = load_activity_state(user_id)
        state["pings_count"] = state.get("pings_count", 0) + 1
        save_activity_state(user_id, state)
        # Note: Activity panel refresh is handled in handler_rideshare if needed