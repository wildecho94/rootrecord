# RootRecord Core_Files/gps_tracker_core.py
# Edited Version: 1.42.20260112

"""
GPS Tracker core logic - geocoding & full data storage
Stores every piece of data received/derived (including edits), prints readable one-line summary.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

DB_PATH = Path(__file__).parent.parent / "data" / "rootrecord.db"
geolocator = Nominatim(user_agent="rootrecord_gps_tracker")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                message_id INTEGER NOT NULL,
                original_timestamp TEXT NOT NULL,
                edit_timestamp TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                heading REAL,
                horizontal_accuracy REAL,
                address TEXT,
                city TEXT,
                country TEXT,
                postal_code TEXT,
                neighborhood TEXT,
                raw_geopy_data TEXT,
                full_record_text TEXT
            )
        ''')
        conn.commit()

def process_location(update):
    """Process location (new or edited), store all fields, print readable line"""
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
    original_timestamp = datetime.fromtimestamp(msg.date).isoformat() if msg.date else datetime.utcnow().isoformat()
    edit_timestamp = datetime.fromtimestamp(msg.edit_date).isoformat() if msg.edit_date else None
    latitude = loc.latitude
    longitude = loc.longitude
    heading = loc.heading if hasattr(loc, 'heading') else None
    horizontal_accuracy = loc.horizontal_accuracy if hasattr(loc, 'horizontal_accuracy') else None

    address = city = country = postal = neighborhood = raw_data = None

    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True, timeout=10)
        if location:
            raw_data = str(location.raw)
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

    # Build readable one-line summary
    edit_note = f" (edited at {edit_timestamp})" if edit_timestamp else ""
    heading_note = f" | Heading: {heading}°" if heading else ""
    accuracy_note = f" | Acc: ±{horizontal_accuracy}m" if horizontal_accuracy else ""
    readable = (
        f"User: {first_name} {last_name} (@{username}, id:{user_id}) | "
        f"Msg ID: {message_id}{edit_note} | Time: {original_timestamp} | "
        f"Location: {latitude:.6f}, {longitude:.6f}{heading_note}{accuracy_note} | "
        f"Address: {address or 'N/A'} | City: {city or 'N/A'} | "
        f"Country: {country or 'N/A'} | Postal: {postal or 'N/A'} | "
        f"Neighborhood: {neighborhood or 'N/A'}"
    )
    print(readable)

    # Store EVERYTHING
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO gps_records 
            (user_id, username, first_name, last_name, message_id, original_timestamp, edit_timestamp,
             latitude, longitude, heading, horizontal_accuracy,
             address, city, country, postal_code, neighborhood,
             raw_geopy_data, full_record_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, first_name, last_name, message_id, original_timestamp, edit_timestamp,
            latitude, longitude, heading, horizontal_accuracy,
            address, city, country, postal, neighborhood,
            raw_data, readable
        ))
        conn.commit()

    print("[gps_tracker_core] Location fully stored")