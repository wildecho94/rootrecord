# Core_Files/db_postgres.py
# Version: 20260117 – Single PostgreSQL connection file (auto-creates config, local only)

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
        # Auto-create with fake/test values (edit later!)
        fake_config = {
            "postgres_user": "postgres",
            "postgres_password": "rootrecord123",
            "postgres_db": "rootrecord"
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(fake_config, f, indent=2)
        print(f"[db_postgres] Created {CONFIG_PATH.name} with fake/test credentials.")
        print("  → Edit it with your real PostgreSQL password!")
        print("  → Add config_postgres.json to .gitignore to keep it private.")
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
    f"@localhost:5432/{config['postgres_db']}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Change to True for query logging during testing
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_postgres():
    print("[db_postgres] Testing PostgreSQL connection...")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
    print(f"[db_postgres] PostgreSQL connected! Version: {version}")
    print("[db_postgres] Ready – single local DB (localhost only)")