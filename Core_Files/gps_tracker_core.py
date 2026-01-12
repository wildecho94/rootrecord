# RootRecord Core_Files/gps_tracker_core.py
# Edited Version: 1.42.20260111

"""
GPS Tracker core logic - geocoding & database storage
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
                timestamp TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT,
                city TEXT,
                country TEXT,
                postal_code TEXT,
                raw_geopy_data TEXT
            )
        ''')
        conn.commit()

def process_location(user_id: int, latitude: float, longitude: float):
    timestamp = datetime.utcnow().isoformat()
    address = city = country = postal = None
    raw_data = None

    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True, timeout=10)
        if location:
            raw_data = str(location.raw)
            address = location.address
            city = location.raw.get('address', {}).get('city') or \
                   location.raw.get('address', {}).get('town') or \
                   location.raw.get('address', {}).get('village')
            country = location.raw.get('address', {}).get('country')
            postal = location.raw.get('address', {}).get('postcode')
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"[gps_tracker_core] Geocoding timeout/unavailable: {e}")
    except Exception as e:
        print(f"[gps_tracker_core] Geocoding error: {e}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO gps_records 
            (user_id, timestamp, latitude, longitude, address, city, country, postal_code, raw_geopy_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, timestamp, latitude, longitude, address, city, country, postal, raw_data))
        conn.commit()

    print(f"[gps_tracker] Stored location for user {user_id}: {latitude}, {longitude}")