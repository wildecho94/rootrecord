# commands/lastping_cmd.py
# Displays the most recent enriched ping (GPS + geopy data)

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.db_mysql import get_db
from sqlalchemy import text

async def cmd_lastping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async for session in get_db():
        # Get latest ping + enriched data for this user
        result = await session.execute(text('''
            SELECT 
                g.latitude, g.longitude, g.timestamp,
                e.address, e.city, e.country, e.distance_m
            FROM gps_records g
            LEFT JOIN geopy_enriched e ON g.id = e.ping_id
            WHERE g.user_id = :user_id
            ORDER BY g.id DESC
            LIMIT 1
        '''), {"user_id": user_id})
        
        row = result.fetchone()
        if row:
            lat, lon, ts, addr, city, country, dist = row
            reply = (
                f"**Latest Ping**\n"
                f"Time: {ts}\n"
                f"Location: {lat:.6f}, {lon:.6f}\n"
                f"Address: {addr or 'Unknown'}\n"
                f"City: {city or 'Unknown'}, {country or 'Unknown'}\n"
                f"Distance from prev: {dist:.1f} m" if dist is not None else "No previous ping"
            )
        else:
            reply = "No pings recorded yet. Send a location to start logging."

    await update.message.reply_text(reply, parse_mode="Markdown")
    print(f"[lastping] User {user_id} requested latest ping")

handler = CommandHandler("lastping", cmd_lastping)