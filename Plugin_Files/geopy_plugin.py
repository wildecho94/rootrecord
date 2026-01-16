# Plugin_Files/geopy_plugin.py
# Version: 1.42.20260117 – Enhanced logging + exported enrich_ping for triggering
# Now fully async, verbose prints, handles no previous ping gracefully

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from utils.db_mysql import get_db, init_mysql

ROOT = Path(__file__).parent.parent
USER_AGENT = "RootRecordBot/1.42 (contact: wildecho94@gmail.com)"

geolocator = Nominatim(user_agent=USER_AGENT)

async def init_db():
    print("[geopy_plugin] Creating/updating geopy_enriched table in MySQL...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS geopy_enriched (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ping_id INT NOT NULL,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                address TEXT,
                city TEXT,
                country TEXT,
                distance_m DOUBLE,
                original_timestamp DATETIME NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_ping_id (ping_id)
            )
        '''))
        await session.commit()

        try:
            await session.execute(text('''
                CREATE INDEX idx_ping_id ON geopy_enriched (ping_id)
            '''))
            await session.commit()
            print("[geopy_plugin] Created index idx_ping_id")
        except Exception as e:
            if "Duplicate key name" in str(e):
                print("[geopy_plugin] Index idx_ping_id already exists")
            else:
                print(f"[geopy_plugin] Index creation failed: {e}")
    print("[geopy_plugin] Geopy table ready")

async def get_last_ping_location(ping_id: int):
    """Get lat/lon of the previous ping for the same user (before this ping_id)"""
    async for session in get_db():
        result = await session.execute(text('''
            SELECT latitude, longitude
            FROM gps_records
            WHERE id < :ping_id
            ORDER BY id DESC
            LIMIT 1
        '''), {"ping_id": ping_id})
        row = result.fetchone()
        if row:
            return row[0], row[1]
    return None, None

async def enrich_ping(ping_id: int, lat: float, lon: float):
    """
    Main enrichment function – called after every new ping save.
    Reverse geocodes + calculates distance from previous ping.
    """
    print(f"[geopy] Starting enrichment for ping_id={ping_id} at ({lat:.6f}, {lon:.6f})")

    address = city = country = None
    distance_m = None

    try:
        location = await asyncio.to_thread(
            geolocator.reverse,
            (lat, lon),
            exactly_one=True,
            timeout=10
        )
        if location:
            raw = location.raw.get('address', {})
            address = location.address
            city = raw.get('city') or raw.get('town') or raw.get('village') or 'Unknown'
            country = raw.get('country', 'Unknown')
            print(f"[geopy] Geocoded: {city}, {country} – {address[:80]}...")
        else:
            print("[geopy] No geocoding result")
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"[geopy] Geocoder timeout/unavailable: {e}")
    except Exception as e:
        print(f"[geopy] Geocoding error: {type(e).__name__}: {e}")

    # Distance from previous ping
    prev_lat, prev_lon = await get_last_ping_location(ping_id)
    if prev_lat is not None and prev_lon is not None:
        try:
            distance_m = geodesic((prev_lat, prev_lon), (lat, lon)).meters
            print(f"[geopy] Distance from previous ping: {distance_m:.0f} m")
        except Exception as e:
            print(f"[geopy] Distance calc error: {e}")

    # Save enriched data
    try:
        async for session in get_db():
            await session.execute(text('''
                INSERT INTO geopy_enriched (
                    ping_id, latitude, longitude,
                    address, city, country,
                    distance_m, original_timestamp
                ) VALUES (
                    :ping_id, :latitude, :longitude,
                    :address, :city, :country,
                    :distance_m, NOW()
                )
                ON DUPLICATE KEY UPDATE
                    address=VALUES(address),
                    city=VALUES(city),
                    country=VALUES(country),
                    distance_m=VALUES(distance_m)
            '''), {
                "ping_id": ping_id,
                "latitude": lat,
                "longitude": lon,
                "address": address,
                "city": city,
                "country": country,
                "distance_m": distance_m
            })
            await session.commit()
        print(f"[geopy] SUCCESS: Enriched data saved/updated for ping {ping_id}")
    except Exception as e:
        print(f"[geopy] Save failed: {e}")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[geopy_plugin] Initialized – enrich_ping ready to be called on new pings")