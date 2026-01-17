# Plugin_Files/uptime_plugin.py
# Version: 1.42.20260117 – Migrated to MySQL (async, unified DB)
#         Removed SQLite – now uses shared db_mysql.py helper
#         Tables: uptime_records, uptime_stats
#         Periodic: every 60s print + save snapshot
#         /uptime command: real stats reply

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text

from utils.db_mysql import get_db, init_mysql
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def init_db():
    print("[uptime_plugin] Creating/updating uptime tables in MySQL...")
    async for session in get_db():
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS uptime_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(10) NOT NULL,  -- start, stop, crash
                timestamp DATETIME NOT NULL
            )
        '''))
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS uptime_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                uptime_pct DECIMAL(5,3) NOT NULL,
                total_up VARCHAR(50) NOT NULL,
                total_down VARCHAR(50) NOT NULL,
                status VARCHAR(10) NOT NULL
            )
        '''))
        await session.commit()
    print("[uptime_plugin] Uptime tables ready in MySQL")

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

    # If still running, add time to now
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
    last_event_time = f"{last_event_type} at {last_ts}" if last_ts else "N/A"

    stats = {
        "uptime_pct": uptime_pct,
        "total_up": format_td(total_up),
        "total_down": format_td(total_down),
        "status": status,
        "last_event_time": last_event_time
    }
    print(f"[UPTIME] {datetime.utcnow()} UTC | Up: {stats['total_up']} | Down: {stats['total_down']} | {stats['uptime_pct']:.3f}% | Status: {stats['status']}")
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
        f"**Lifetime Uptime Stats**\n"
        f"• Status: **{stats['status'].upper()}**\n"
        f"• Uptime percentage: **{stats['uptime_pct']:.3f}%**\n"
        f"• Total uptime: **{stats['total_up']}**\n"
        f"• Total downtime: **{stats['total_down']}**\n"
        f"• Last event: {stats['last_event_time'] or 'N/A'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def initialize():
    asyncio.create_task(init_mysql())
    asyncio.create_task(init_db())
    asyncio.create_task(periodic_update())

    # Register /uptime command
    from telegram.ext import Application
    def register(app: Application):
        app.add_handler(CommandHandler("uptime", cmd_uptime))
        print("[uptime_plugin] /uptime command registered")

    # Record initial start on every launch
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO uptime_records (event_type, timestamp)
            VALUES ('start', NOW())
        '''))
        await session.commit()
    print("[uptime_plugin] Initial start recorded in MySQL")

    print("[uptime_plugin] Initialized – MySQL mode, periodic updates every 60s")

# Graceful shutdown hook (record stop)
import atexit

async def on_shutdown():
    async for session in get_db():
        await session.execute(text('''
            INSERT INTO uptime_records (event_type, timestamp)
            VALUES ('stop', NOW())
        '''))
        await session.commit()
    print("[uptime_plugin] Shutdown recorded in MySQL")

atexit.register(lambda: asyncio.run(on_shutdown()))