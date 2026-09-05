import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path so both 'python bot/main.py' and 'python -m bot.main' work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Web server for deployment platforms requiring a bound port (e.g. Render)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

from telegram import Update
from bot.config import config
from database.db import init_db
from bot.handlers.start import (
    start_command, receive_nickname, cancel, WAITING_NICKNAME,
    handle_approve, handle_reject
)
from bot.handlers.checkin import handle_checkin, handle_checkout, handle_location, handle_location_type
from bot.handlers.profile import handle_profile
from bot.handlers.leaderboard import handle_leaderboard
from bot.handlers.admin import (
    handle_admin_menu, handle_add_schedule_start, receive_nickname_for_schedule,
    receive_day, receive_start_time, receive_end_time,
    handle_view_employees, handle_view_schedules, handle_view_rejected,
    handle_unreject_command, handle_unblock_callback,
    WAITING_NICKNAME_FOR_SCHEDULE, WAITING_DAY, WAITING_START_TIME, WAITING_END_TIME
)
from bot.handlers.anonymous import (
    start_anonymous_message, receive_anonymous_message, cancel_anonymous_message,
    WAITING_ANON_MESSAGE
)
from bot.handlers.callbacks import handle_cancel
from bot.services.auto_checkout import auto_checkout_service
from bot.keyboards.inline import (
    BTN_CHECKIN, BTN_CHECKOUT, BTN_PROFILE, BTN_LEADERBOARD,
    BTN_ANONYMOUS, BTN_ADMIN
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize database and services after bot starts"""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    auto_checkout_service.start()
    logger.info("Auto checkout service started")


def main():
    """Start the bot"""
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    # ── Registration conversation ────────────────────────────────────────────
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            WAITING_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nickname)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # ── Admin schedule conversation ──────────────────────────────────────────
    schedule_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_add_schedule_start, pattern='^admin_add_schedule$')],
        states={
            WAITING_NICKNAME_FOR_SCHEDULE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nickname_for_schedule)
            ],
            WAITING_DAY: [CallbackQueryHandler(receive_day, pattern=r'^day_\d+$')],
            WAITING_START_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_time)
            ],
            WAITING_END_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_time)
            ]
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern='^cancel$')]
    )

    # ── Anonymous message conversation ───────────────────────────────────────
    anonymous_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f'^{BTN_ANONYMOUS}$'), start_anonymous_message),
            CommandHandler('anonymous', start_anonymous_message),
        ],
        states={
            WAITING_ANON_MESSAGE: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, receive_anonymous_message)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_anonymous_message),
            CallbackQueryHandler(cancel_anonymous_message, pattern='^cancel$')
        ]
    )

    application.add_handler(registration_handler)
    application.add_handler(schedule_handler)
    application.add_handler(anonymous_handler)

    # ── Admin command handlers ───────────────────────────────────────────────
    application.add_handler(CommandHandler('unreject', handle_unreject_command))

    # ── Live location handler ────────────────────────────────────────────────
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # ── Inline callback handlers ─────────────────────────────────────────────
    application.add_handler(CallbackQueryHandler(handle_cancel, pattern='^cancel$'))
    application.add_handler(CallbackQueryHandler(handle_approve, pattern=r'^approve_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_reject,  pattern=r'^reject_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_unblock_callback, pattern=r'^unblock_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_location_type, pattern='^loc_(campus|rocketchat)$'))
    application.add_handler(CallbackQueryHandler(handle_admin_menu, pattern='^admin_menu$'))
    application.add_handler(CallbackQueryHandler(handle_view_employees, pattern='^admin_view_employees$'))
    application.add_handler(CallbackQueryHandler(handle_view_schedules, pattern='^admin_view_schedules$'))
    application.add_handler(CallbackQueryHandler(handle_view_rejected, pattern='^admin_view_rejected$'))

    # ── Reply keyboard (bottom) text handlers ────────────────────────────────
    application.add_handler(MessageHandler(filters.Regex(f'^{BTN_CHECKIN}$'), handle_checkin))
    application.add_handler(MessageHandler(filters.Regex(f'^{BTN_CHECKOUT}$'), handle_checkout))
    application.add_handler(MessageHandler(filters.Regex(f'^{BTN_PROFILE}$'), handle_profile))
    application.add_handler(MessageHandler(filters.Regex(f'^{BTN_LEADERBOARD}$'), handle_leaderboard))
    application.add_handler(MessageHandler(filters.Regex(f'^{BTN_ADMIN}$'), handle_admin_menu))

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
