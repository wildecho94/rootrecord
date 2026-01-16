# Plugin_Files/geopy_plugin.py
# Version: 1.43.20260117 – Migrated to self-hosted MySQL (async, single DB, no locks, fixed syntax)

import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from utils.db_mysql import get_db, init_mysql  # Shared self-hosted MySQL helper

ROOT = Path(__file__).parent.parent
USER_AGENT = "RootRecordBot/1.0 (contact: wildecho94@gmail.com)"

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
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    print("[geopy_plugin] Geopy table and index ready in MySQL")

async def get_last_ping(vehicle_id: int = None):
    async for session in get_db():
        query = text('''
            SELECT latitude, longitude
            FROM gps_records
        ''')
        params = {}
        if vehicle_id is not None:
            query = text('''
                SELECT latitude, longitude
                FROM gps_records
                WHERE vehicle_id = :vehicle_id
            ''')
            params = {"vehicle_id": vehicle_id}
        query = query + text(" ORDER BY timestamp DESC LIMIT 1")

        result = await session.execute(query, params)
        last_ping = result.fetchone()
        return last_ping if last_ping else (None, None)

async def enrich_ping(ping_id: int, lat: float, lon: float, original_timestamp: datetime, vehicle_id: int = None):
    try:
        address = city = country = 'No address found'
        try:
            location = await asyncio.get_running_loop().run_in_executor(None, geolocator.reverse, f"{lat}, {lon}", None, "en")
            if location:
                address = location.address
                raw = location.raw.get('address', {})
                city = raw.get('city', raw.get('town', raw.get('village', 'Unknown')))
                country = raw.get('country', 'Unknown')
        except Exception as e:
            print(f"[geopy] Geocoding error: {e}")

        distance_m = None
        prev_lat, prev_lon = await get_last_ping(vehicle_id)
        if prev_lat is not None and prev_lon is not None:
            distance_m = geodesic((prev_lat, prev_lon), (lat, lon)).meters
            print(f"[geopy] Distance from previous: {distance_m:.0f} m")

        async for session in get_db():
            await session.execute(text('''
                INSERT INTO geopy_enriched (
                    ping_id, latitude, longitude,
                    address, city, country,
                    distance_m, original_timestamp
                ) VALUES (:ping_id, :latitude, :longitude, :address, :city, :country, :distance_m, :original_timestamp)
            '''), {
                "ping_id": ping_id,
                "latitude": lat,
                "longitude": lon,
                "address": address,
                "city": city,
                "country": country,
                "distance_m": distance_m,
                "original_timestamp": original_timestamp
            })
            await session.commit()
        print(f"[geopy] SUCCESS: Enriched data saved for ping {ping_id}")

    except Exception as e:
        print(f"[geopy] Enrichment failed: {e}")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    print("[geopy_plugin] Initialized – waiting for pings to enrich")