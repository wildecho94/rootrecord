# utils/db_mysql.py
# Note: MySQL data dir is now I:\MYSQL (check my.ini: datadir=I:/MYSQL/data)

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Load from config_mysql.json (in root)
import json
with open("config_mysql.json", "r") as f:
    config = json.load(f)

MYSQL_USER = config.get("mysql_user", "root")
MYSQL_PASS = config.get("mysql_password", "")
MYSQL_HOST = config.get("mysql_host", "localhost")
MYSQL_PORT = config.get("mysql_port", 3306)
MYSQL_DB   = config.get("mysql_db", "rootrecord")

ENGINE_URL = f"mysql+asyncmy://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"

engine = create_async_engine(ENGINE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

async def init_mysql():
    print("[db_mysql] Testing MySQL connection...")
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print(f"[db_mysql] MySQL connected! Version: {await get_version()}")

async def get_version():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT VERSION()"))
        return result.scalar()