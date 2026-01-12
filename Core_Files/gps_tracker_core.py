# RootRecord Core_Files/gps_tracker_core.py
# Edited Version: 1.42.20260111

"""
GPS Tracker core logic - geocoding & database storage
Stores every piece of received/derived data in readable format.
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
                timestamp TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
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

def process_location(update: Update):
    """Process full location share + user info, store everything, print readable line"""
    if not update.message or not update.message.location:
        return

    msg = update.message
    user = msg.from_user
    loc = msg.location

    user_id = user.id
    username = user.username or "[no username]"
    first_name = user.first_name or "[no name]"
    last_name = user.last_name or ""
    timestamp = datetime.utcnow().isoformat()
    latitude = loc.latitude
    longitude = loc.longitude

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
    readable = (
        f"User: {first_name} {last_name} (@{username}, id:{user_id}) | "
        f"Time: {timestamp} | "
        f"Location: {latitude:.6f}, {longitude:.6f} | "
        f"Address: {address or 'N/A'} | "
        f"City: {city or 'N/A'} | Country: {country or 'N/A'} | "
        f"Postal: {postal or 'N/A'} | Neighborhood: {neighborhood or 'N/A'}"
    )
    print(readable)

    # Store EVERYTHING
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO gps_records 
            (user_id, username, first_name, last_name, timestamp, latitude, longitude,
             address, city, country, postal_code, neighborhood, raw_geopy_data, full_record_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, first_name, last_name, timestamp, latitude, longitude,
            address, city, country, postal, neighborhood, raw_data, readable
        ))
        conn.commit()

    print("[gps_tracker_core] Location fully stored")