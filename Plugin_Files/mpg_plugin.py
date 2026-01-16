# Plugin_Files/mpg_plugin.py
# Version: 20260118 – Migrated to MySQL; now thin wrapper using vehicles_plugin logic

"""
MPG plugin – /mpg command to view per-vehicle fuel efficiency
Delegates calculations to vehicles_plugin (shared MySQL tables & logic)
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Reuse shared helpers from vehicles_plugin
from .vehicles_plugin import get_user_vehicles, calculate_fuel_stats

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vehicles = await get_user_vehicles(user_id)

    if not vehicles:
        await update.message.reply_text("No vehicles found. Add one with /vehicle add first.")
        return

    text = "**Fuel Efficiency Stats**\n\n"
    has_data = False

    for vid, plate, year, make, model, _ in vehicles:
        stats = await calculate_fuel_stats(vid)
        if stats:
            has_data = True
            text += f"**{year} {make} {model} ({plate})**\n"
            text += f"  • Overall MPG: **{stats['mpg']:.1f}**\n"
            text += f"  • Total miles: **{stats['miles']}** mi\n"
            text += f"  • Total fuel: **{stats['gallons']:.2f}** gal\n"
            text += f"  • Total fuel cost: **${stats['cost']:.2f}**\n"
            text += f"  • Cost per mile: **${stats['cost_per_mile']:.3f}**\n"
            text += f"  • Intervals counted: {stats['fill_count']}\n"
            text += f"  • Period: {stats['period_start']} to {stats['period_end']}\n\n"
        else:
            text += f"**{year} {make} {model} ({plate})**: Not enough fill-up data (need odometer + multiple fills)\n\n"

    if not has_data:
        text += "No usable fuel data yet. Log fill-ups with /fillup (include odometer)."

    await update.message.reply_text(text, parse_mode="Markdown")

def initialize():
    print("[mpg_plugin] Initialized – /mpg command ready (using MySQL via vehicles_plugin)")