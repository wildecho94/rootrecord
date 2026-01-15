# Core_Files/db_postgres.py
# Version: 1.43.20260117 – Local PostgreSQL connection (secure config.json load)

import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config_postgres.json"

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH.name}! Create it in root with:\n"
            "{\n"
            '  "postgres_user": "postgres",\n'
            '  "postgres_password": "your_password",\n'
            '  "postgres_db": "rootrecord"\n'
            "}\n"
            "Add to .gitignore!"
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    required = ["postgres_user", "postgres_password", "postgres_db"]
    for key in required:
        if key not in config or not config[key]:
            raise ValueError(f"Missing '{key}' in {CONFIG_PATH.name}")

    return config

config = load_config()

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{config['postgres_user']}:{config['postgres_password']}"
    f"@localhost:5432/{config['postgres_db']}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
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
    print("[db_postgres] Testing single PostgreSQL connection...")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
    print(f"[db_postgres] Connected! PostgreSQL version: {version}")
    print("[db_postgres] Ready – all data in one local DB (localhost only)")