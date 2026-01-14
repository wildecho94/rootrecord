# commands/uptime_cmd.py
# Moved from uptime_plugin.py to be auto-loaded by cmd_loader.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from datetime import timedelta

# Import the stats calculator from the plugin (adjust path if your structure differs)
from Plugin_Files.uptime_plugin import calculate_uptime_stats

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = calculate_uptime_stats()
    up_str = str(timedelta(seconds=s['total_up_sec']))
    down_str = str(timedelta(seconds=s['total_down_sec']))
    text = (
        f"**Uptime Statistics**\n"
        f"• Status: **{s['status'].upper()}**\n"
        f"• Total uptime: {up_str}\n"
        f"• Total downtime: {down_str}\n"
        f"• Uptime percentage: **{s['uptime_pct']:.3f}%**\n"
        f"• Last event: {s['last_event_time'] or 'N/A'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

handler = CommandHandler("uptime", cmd_uptime)