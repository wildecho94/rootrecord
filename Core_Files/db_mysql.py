# Core_Files/db_mysql.py
# Version: 20260117 – Self-hosted local MySQL 9.5 connection (secure config.json load)

import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config_mysql.json"

def load_or_create_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        # Auto-create with fake/test values (edit with real ones!)
        fake_config = {
            "mysql_user": "root",
            "mysql_password": "rootrecord123",
            "mysql_db": "rootrecord"
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(fake_config, f, indent=2)
        print(f"[db_mysql] Created project-local {CONFIG_PATH.name} with fake/test credentials.")
        print("  → Edit it with your real MySQL password!")
        print("  → Add config_mysql.json to .gitignore to keep it private!")
        config = fake_config

    required = ["mysql_user", "mysql_password", "mysql_db"]
    for key in required:
        if key not in config or not config[key]:
            raise ValueError(f"Missing or empty '{key}' in {CONFIG_PATH.name}")

    return config

config = load_or_create_config()

DATABASE_URL = (
    f"mysql+asyncmy://"
    f"{config['mysql_user']}:{config['mysql_password']}"
    f"@localhost:3306/{config['mysql_db']}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,                  # Change to True for query logging during testing
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

async def init_mysql():
    print("[db_mysql] Testing MySQL connection...")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT VERSION()"))
        version = result.scalar()
    print(f"[db_mysql] MySQL connected! Version: {version}")
    print("[db_mysql] Ready – single self-hosted local DB (localhost only)")