# Core_Files/telegram_core.py
"""
Telegram plugin core — bot startup, polling, handler registration
"""

print("[telegram] core loaded")

from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import Update
from Plugin_Files.telegram import load_config, register_user
import logging
from datetime import datetime

# Import handlers from the handler file
from Handler_Files.telegram_handler import button_callback  # ← Uncommented & active

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global application instance (accessible for future plugins to add handlers)
application = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f"Hello {user.first_name or 'user'}! Bot is now active.\n"
        "Use /help for commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — Start the bot\n"
        "/help — This message\n"
        "/status — Show current config status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    enabled = [k for k, v in config["connections"].items() if v["enabled"]]
    await update.message.reply_text(
        f"Bot enabled: {config['enabled']}\n"
        f"Connections: {', '.join(enabled) or 'none'}\n"
        f"Token set: {'yes' if not config['bot_token'].startswith('YOUR_') else 'no'}"
    )


async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log every text message"""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    log_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user.username or user.id} in {chat.type} ({chat.id}): {msg.text or '[non-text]'}"
    print(log_line)

    log_file = BASE_DIR / "logs" / "telegram.log"
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def start_bot():
    global application

    config = load_config()
    if not config["enabled"] or config["bot_token"].startswith("YOUR_"):
        print("[telegram] Bot disabled or no token — skipping startup")
        return

    print("[telegram] Starting Telegram bot polling...")

    application = Application.builder().token(config["bot_token"]).build()

    # Basic commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))

    # Log all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))

    # Register advanced handlers from telegram_handler.py
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start polling
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=0.5
    )


def initialize():
    start_bot()


if __name__ == "__main__":
    initialize()