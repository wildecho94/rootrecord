# Plugin_Files/geopy_plugin.py
# Version: 20260113 – Geopy enrichment (separate table, original timestamps)

"""
Geopy plugin – reverse geocoding + distance between pings
All enriched data saved SEPARATELY in geopy_enriched
Uses original raw timestamp from gps_records
received_at = when enrichment ran (processing time)
No deletion of raw gps_records rows
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Paths & Config
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "rootrecord.db"
USER_AGENT = "RootRecordBot/1.0 (contact: wildecho94@gmail.com)"

geolocator = Nominatim(user_agent=USER_AGENT)

def init_db():
    print("[geopy_plugin] Creating geopy_enriched table if missing...")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS geopy_enriched (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ping_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT,
                city TEXT,
                country TEXT,
                distance_m REAL,
                original_timestamp TEXT NOT NULL,
                enriched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(ping_id) REFERENCES gps_records(id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ping_id ON geopy_enriched (ping_id)')
        conn.commit()
    print("[geopy_plugin] Geopy enrichment table ready")

def enrich_ping(ping_id: int, lat: float, lon: float, original_timestamp: str, prev_lat=None, prev_lon=None):
    print(f"[geopy] Enriching ping {ping_id}: ({lat:.6f}, {lon:.6f}) @ {original_timestamp}")

    # Reverse geocode
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
        if location:
            raw = location.raw
            address = raw.get('display_name', 'No address')
            city = raw['address'].get('city') or raw['address'].get('town') or 'Unknown'
            country = raw['address'].get('country', 'Unknown')
        else:
            address = city = country = 'No address found'
    except Exception as e:
        print(f"[geopy] Geocoding error: {e}")
        address = city = country = 'Geopy failed'

    # Distance
    distance_m = None
    if prev_lat is not None and prev_lon is not None:
        distance_m = geodesic((prev_lat, prev_lon), (lat, lon)).meters
        print(f"[geopy] Distance from previous: {distance_m:.0f} m")

    # Save (original timestamp preserved)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO geopy_enriched (
                    ping_id, latitude, longitude,
                    address, city, country,
                    distance_m, original_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ping_id, lat, lon, address, city, country, distance_m, original_timestamp))
            conn.commit()
        print(f"[geopy] SUCCESS: Enriched data saved for ping {ping_id}")
    except sqlite3.Error as e:
        print(f"[geopy] Save failed: {e}")

def initialize():
    init_db()
    print("[geopy_plugin] Initialized – waiting for pings to enrich")