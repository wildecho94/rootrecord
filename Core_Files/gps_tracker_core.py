# Core_Files/gps_tracker_core.py
# Part of RootRecord GPS Tracker Plugin
# Version: 1.42.20260112 (edited with process_location)

"""
Core database functions for GPS tracking
Handles initialization and saving location records
"""

import sqlite3
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional

# Setup logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("gps_tracker_core")

# Database path (relative to project root)
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "rootrecord.db"

def ensure_data_dir():
    """Create data directory if it doesn't exist"""
    DATA_DIR.mkdir(exist_ok=True)

def init_db():
    """Initialize the database and create gps_records table if needed"""
    ensure_data_dir()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gps_records (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                username        TEXT,
                first_name      TEXT,
                last_name       TEXT,
                chat_id         INTEGER NOT NULL,
                message_id      INTEGER,
                latitude        REAL NOT NULL,
                longitude       REAL NOT NULL,
                accuracy        REAL,
                heading         REAL,
                speed           REAL,
                altitude        REAL,
                live_period     INTEGER,
                timestamp       TEXT NOT NULL,          -- ISO format
                received_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, user_id) ON CONFLICT IGNORE
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON gps_records (user_id, timestamp)
        ''')
        
        conn.commit()
        logger.info(f"Database initialized successfully at: {DB_PATH}")
        print(f"[gps_tracker_core] DB table gps_records ready at {DB_PATH}")
        
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"[gps_tracker_core] ERROR: Database init failed - {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def save_gps_record(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    accuracy: Optional[float] = None,
    heading: Optional[float] = None,
    speed: Optional[float] = None,
    altitude: Optional[float] = None,
    live_period: Optional[int] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Save a GPS location record to the database.
    Returns True if saved successfully, False otherwise.
    """
    if latitude is None or longitude is None:
        logger.warning("Missing latitude or longitude - record not saved")
        return False

    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO gps_records (
                user_id, username, first_name, last_name,
                chat_id, message_id,
                latitude, longitude, accuracy, heading, speed, altitude,
                live_period, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, first_name, last_name,
            chat_id, message_id,
            latitude, longitude, accuracy, heading, speed, altitude,
            live_period, timestamp
        ))
        
        conn.commit()
        logger.info(f"Saved GPS record for user {user_id} at ({latitude}, {longitude})")
        print(f"[gps_tracker_core] Saved location for user {user_id}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Failed to save GPS record: {e}")
        print(f"[gps_tracker_core] ERROR saving record: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def process_location(user_id, username, latitude, longitude, accuracy=None, heading=None, **kwargs):
    """
    Compatibility function expected by gps_tracker_handler.py
    Forwards the data to save_gps_record()
    """
    timestamp = kwargs.get('timestamp') or datetime.utcnow().isoformat()
    
    success = save_gps_record(
        user_id=user_id,
        username=username,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        heading=heading,
        timestamp=timestamp,
        **kwargs  # pass any extra fields like first_name, chat_id, etc.
    )
    
    return success

# Optional: for debugging
def get_recent_records(limit=5):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gps_records ORDER BY received_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        return rows
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch recent records: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()