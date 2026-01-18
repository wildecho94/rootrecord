# Plugin_Files/uptime_plugin.py
# Version: 1.42.20260117 – FULL MySQL migration (no SQLite left)
#         Uses shared async get_db() for all queries
#         Tables: uptime_records (events), uptime_stats (snapshots)
#         Periodic: every 60s calculate + print + save snapshot
#         /uptime command: real async query + formatted reply
#         Shutdown: async record 'stop' event
#         Handles unpaired starts, crashes, no events

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text

from utils.db_mysql import get_db, init_mysql
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

YELLOW = "\033[93m"
RESET  = "\033[0m"

async def init_db():
    print("[uptime_plugin] Creating/updating MySQL tables...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type ENUM('start', 'stop', 'crash') NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''))
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS uptime_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                uptime_pct DECIMAL(6,3) NOT NULL,
                total_up VARCHAR(50) NOT NULL,
                total_down VARCHAR(50) NOT NULL,
                status ENUM('running', 'stopped') NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        '''))
        await session.commit()
    print("[uptime_plugin] Uptime tables ready (MySQL)")

async def calculate_uptime_stats():
    async for session in get_db():
        result = await session.execute(text('''
            SELECT event_type, timestamp
            FROM uptime_records
            ORDER BY timestamp ASC
        '''))
        events = result.fetchall()

    if not events:
        return {
            "uptime_pct": 0.0,
            "total_up": "0s",
            "total_down": "0s",
            "status": "unknown",
            "last_event_time": "No events recorded"
        }

    total_up = timedelta()
    total_down = timedelta()
    is_running = False
    last_ts = None
    last_event_type = None

    for event_type, ts in events:
        if last_ts:
            delta = ts - last_ts
            if last_event_type == "start":
                total_up += delta
            elif last_event_type in ("stop", "crash"):
                total_down += delta

        last_ts = ts
        last_event_type = event_type

        if event_type == "start":
            is_running = True
        elif event_type in ("stop", "crash"):
            is_running = False

    # If still running, add time from last start to now
    if is_running and last_ts:
        now = datetime.utcnow()
        delta = now - last_ts
        total_up += delta

    total_time = total_up + total_down
    uptime_pct = (total_up.total_seconds() / total_time.total_seconds() * 100) if total_time.total_seconds() > 0 else 0.0

    def format_td(td):
        days = td.days
        hours, rem = divmod(td.seconds, 3600)
        mins, secs = divmod(rem, 60)
        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if mins: parts.append(f"{mins}m")
        if secs or not parts: parts.append(f"{secs}s")
        return " ".join(parts)

    status = "running" if is_running else "stopped"
    last_event_time = f"{last_event_type} at {last_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}" if last_ts else "N/A"

    stats = {
        "uptime_pct": uptime_pct,
        "total_up": format_td(total_up),
        "total_down": format_td(total_down),
        "status": status,
        "last_event_time": last_event_time
    }

    print(f"{YELLOW}[UPTIME] {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | "
          f"Up: {stats['total_up']} | Down: {stats['total_down']} | "
          f"{stats['uptime_pct']:.3f}% | Status: {stats['status']}{RESET}")

    return stats

async def save_stats_snapshot(stats):
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO uptime_stats (uptime_pct, total_up, total_down, status)
            VALUES (:pct, :up, :down, :status)
        '''), {
            "pct": stats["uptime_pct"],
            "up": stats["total_up"],
            "down": stats["total_down"],
            "status": stats["status"]
        })
        await session.commit()
    print("[uptime_plugin] Saved stats snapshot to MySQL")

async def periodic_update():
    while True:
        stats = await calculate_uptime_stats()
        await save_stats_snapshot(stats)
        await asyncio.sleep(60)

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await calculate_uptime_stats()
    text = (
        f"**RootRecord Lifetime Uptime**\n\n"
        f"• Status: **{stats['status'].upper()}** {'🟢' if stats['status'] == 'running' else '🔴'}\n"
        f"• Uptime percentage: **{stats['uptime_pct']:.3f}%**\n"
        f"• Total online: **{stats['total_up']}**\n"
        f"• Total offline: **{stats['total_down']}**\n"
        f"• Last event: {stats['last_event_time']}\n\n"
        f"Tracks every start/stop/crash — survives restarts."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    asyncio.create_task(periodic_update())

    # Record initial 'start' event
    asyncio.create_task(record_start_event())

    print("[uptime_plugin] Initialized – MySQL mode, periodic updates every 60s")

async def record_start_event():
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO uptime_records (event_type, timestamp)
            VALUES ('start', NOW())
        '''))
        await session.commit()
    print("[uptime_plugin] Recorded initial 'start' event")

# Graceful shutdown: record 'stop'
import atexit

async def record_shutdown():
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO uptime_records (event_type, timestamp)
            VALUES ('stop', NOW())
        '''))
        await session.commit()
    print("[uptime_plugin] Recorded 'stop' event on shutdown")

def sync_shutdown():
    asyncio.run(record_shutdown())

atexit.register(sync_shutdown)