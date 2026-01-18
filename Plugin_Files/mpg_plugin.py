# Plugin_Files/mpg_plugin.py
# Version: 1.42.20260117 – Fixed import issue + added basic logging
# Now safely imports from vehicles_plugin without crashing if function missing
# Provides a fallback /mpg command with useful message if stats not ready

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# Safe import – try to get real stats function, fallback if missing
try:
    from .vehicles_plugin import get_user_vehicles, calculate_fuel_stats
    REAL_STATS_AVAILABLE = True
except ImportError as e:
    print(f"[mpg_plugin] Import warning: {e} – using fallback mode")
    REAL_STATS_AVAILABLE = False

    # Dummy fallbacks to prevent crashes
    async def get_user_vehicles(user_id):
        return []

    async def calculate_fuel_stats(vehicle_id):
        return None

async def cmd_mpg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"[mpg] /mpg requested by user {user_id}")

    if not REAL_STATS_AVAILABLE:
        await update.message.reply_text(
            "MPG stats module is in fallback mode (import issue). "
            "Use /vehicles to list your cars for now. "
            "Full MPG calculation coming soon."
        )
        print("[mpg] Responded with fallback message (real stats import failed)")
        return

    vehicles = await get_user_vehicles(user_id)

    if not vehicles:
        await update.message.reply_text(
            "No vehicles found. Add one first with /vehicle add PLATE YEAR MAKE MODEL ODOMETER"
        )
        print(f"[mpg] No vehicles for user {user_id}")
        return

    text = "**Your Fuel Efficiency Summary**\n\n"
    has_data = False

    for vid, plate, year, make, model, initial_odo in vehicles:
        stats = await calculate_fuel_stats(vid)
        if stats and stats.get('fill_count', 0) > 1:
            has_data = True
            text += f"**{year} {make} {model} ({plate})**\n"
            text += f"  • Overall MPG: **{stats['mpg']:.1f}**\n"
            text += f"  • Total miles driven: **{stats['miles']:,}** mi\n"
            text += f"  • Total fuel used: **{stats['gallons']:.2f}** gal\n"
            text += f"  • Total fuel cost: **${stats['cost']:,.2f}**\n"
            text += f"  • Cost per mile: **${stats['cost_per_mile']:.3f}**\n"
            text += f"  • Fill-ups counted: {stats['fill_count']}\n"
            text += f"  • Period: {stats.get('period_start', 'N/A')} to {stats.get('period_end', 'N/A')}\n\n"
            print(f"[mpg] Stats generated for vehicle {vid} ({plate})")
        else:
            text += f"**{year} {make} {model} ({plate})**: Not enough fill-up data yet (need multiple logged with odometer)\n\n"
            print(f"[mpg] Insufficient data for vehicle {vid} ({plate})")

    if not has_data:
        text += "No usable MPG data yet. Log more fill-ups with /fillup (include odometer readings)."

    await update.message.reply_text(text, parse_mode="Markdown")
    print(f"[mpg] /mpg response sent to user {user_id}")

def initialize():
    print("[mpg_plugin] Initialized – /mpg command ready (with fallback if import fails)")