# Core_Files/db_postgres.py
# Version: 20260117 – Auto-creates config.json + rootrecord DB if missing (local only)

import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config_postgres.json"

def load_or_create_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        fake_config = {
            "postgres_user": "postgres",
            "postgres_password": "rootrecord123",
            "postgres_db": "rootrecord"
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(fake_config, f, indent=2)
        print(f"[db_postgres] Created {CONFIG_PATH.name} with fake/test credentials.")
        print("  → Edit it with your real PostgreSQL password!")
        print("  → Add config_postgres.json to .gitignore!")
        config = fake_config

    required = ["postgres_user", "postgres_password", "postgres_db"]
    for key in required:
        if key not in config or not config[key]:
            raise ValueError(f"Missing or empty '{key}' in {CONFIG_PATH.name}")

    return config

config = load_or_create_config()

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{config['postgres_user']}:{config['postgres_password']}"
    f"@localhost:5432/postgres"  # Connect to default 'postgres' DB first
)

# Engine for initial connection (to create DB if needed)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

async def create_database_if_missing():
    print("[db_postgres] Checking/creating database 'rootrecord'...")
    async with engine.connect() as conn:
        # Check if DB exists
        result = await conn.execute(text(
            f"SELECT 1 FROM pg_database WHERE datname = '{config['postgres_db']}'"
        ))
        if not result.scalar():
            print(f"[db_postgres] Database '{config['postgres_db']}' does not exist – creating...")
            await conn.execute(text(f"CREATE DATABASE {config['postgres_db']}"))
            await conn.commit()
            print(f"[db_postgres] Created database '{config['postgres_db']}'")
        else:
            print(f"[db_postgres] Database '{config['postgres_db']}' already exists")

async def init_postgres():
    print("[db_postgres] Initializing PostgreSQL...")
    await create_database_if_missing()

    # Reconnect to the actual DB
    app_db_url = DATABASE_URL.replace("/postgres", f"/{config['postgres_db']}")
    app_engine = create_async_engine(app_db_url, echo=False)
    async with app_engine.begin() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
    print(f"[db_postgres] Connected! PostgreSQL version: {version}")
    print("[db_postgres] Ready – single local DB (localhost only)")