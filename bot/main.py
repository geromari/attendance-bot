import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
import logging
import os
import sys
import warnings
from pathlib import Path

# Add project root to sys.path so both 'python bot/main.py' and 'python -m bot.main' work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

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
    handle_admin_menu,
    handle_weekly_schedule_employees_list, receive_sched_nickname,
    handle_schedule_user_menu,
    handle_sched_preset_prompt, receive_sched_preset_time,
    handle_sched_text_prompt, receive_sched_full_text,
    handle_sched_days_view, handle_sched_edit_single_day,
    handle_sched_dayoff, handle_sched_input_single_day,
    receive_sched_single_day_time,
    handle_sched_clear_confirm, handle_sched_clear_execute,
    handle_setschedule_command, handle_schedule_cancel,
    handle_view_employees, handle_view_schedules, handle_view_rejected,
    handle_unreject_command, handle_unblock_callback,
    handle_remove_employee_list, handle_remove_employee_confirm_prompt,
    handle_remove_employee_execute, handle_remove_employee_command,
    WAITING_SCHED_NICKNAME, WAITING_SCHED_PRESET_TIME,
    WAITING_SCHED_FULL_TEXT, WAITING_SCHED_SINGLE_DAY_TIME
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
        entry_points=[
            CallbackQueryHandler(handle_weekly_schedule_employees_list, pattern=r'^(admin_weekly_schedule|admin_add_schedule)$'),
            CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
            CallbackQueryHandler(handle_sched_preset_prompt, pattern=r'^sched_preset_(5|6|7)_\d+$'),
            CallbackQueryHandler(handle_sched_text_prompt, pattern=r'^sched_text_\d+$'),
            CallbackQueryHandler(handle_sched_input_single_day, pattern=r'^sched_inputday_\d+_\d+$'),
        ],
        states={
            WAITING_SCHED_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sched_nickname),
                CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
                CallbackQueryHandler(handle_schedule_cancel, pattern=r'^(cancel|cancel_schedule|sched_cancel_.*)$'),
                CallbackQueryHandler(handle_admin_menu, pattern=r'^(admin_menu|back_to_main)$'),
            ],
            WAITING_SCHED_PRESET_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sched_preset_time),
                CallbackQueryHandler(handle_schedule_cancel, pattern=r'^(cancel|cancel_schedule|sched_cancel_.*)$'),
                CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
                CallbackQueryHandler(handle_weekly_schedule_employees_list, pattern=r'^(admin_weekly_schedule|admin_add_schedule)$'),
                CallbackQueryHandler(handle_admin_menu, pattern=r'^(admin_menu|back_to_main)$'),
            ],
            WAITING_SCHED_FULL_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sched_full_text),
                CallbackQueryHandler(handle_schedule_cancel, pattern=r'^(cancel|cancel_schedule|sched_cancel_.*)$'),
                CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
                CallbackQueryHandler(handle_weekly_schedule_employees_list, pattern=r'^(admin_weekly_schedule|admin_add_schedule)$'),
                CallbackQueryHandler(handle_admin_menu, pattern=r'^(admin_menu|back_to_main)$'),
            ],
            WAITING_SCHED_SINGLE_DAY_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sched_single_day_time),
                CallbackQueryHandler(handle_schedule_cancel, pattern=r'^(cancel|cancel_schedule|sched_cancel_.*)$'),
                CallbackQueryHandler(handle_sched_days_view, pattern=r'^sched_days_\d+$'),
                CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
                CallbackQueryHandler(handle_admin_menu, pattern=r'^(admin_menu|back_to_main)$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_schedule_cancel, pattern=r'^(cancel|cancel_schedule|sched_cancel_.*)$'),
            CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'),
            CallbackQueryHandler(handle_sched_days_view, pattern=r'^sched_days_\d+$'),
            CallbackQueryHandler(handle_weekly_schedule_employees_list, pattern=r'^(admin_weekly_schedule|admin_add_schedule)$'),
            CallbackQueryHandler(handle_admin_menu, pattern=r'^(admin_menu|back_to_main)$'),
            CommandHandler('cancel', handle_schedule_cancel),
            CommandHandler('admin', handle_admin_menu),
            MessageHandler(filters.Regex(f'^({BTN_ADMIN}|{BTN_CHECKIN}|{BTN_CHECKOUT}|{BTN_PROFILE}|{BTN_LEADERBOARD}|{BTN_ANONYMOUS})$'), handle_admin_menu),
        ],
        per_message=False,
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
    application.add_handler(CommandHandler(['remove', 'fire'], handle_remove_employee_command))
    application.add_handler(CommandHandler('setschedule', handle_setschedule_command))

    # ── Live location handler ────────────────────────────────────────────────
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # ── Inline callback handlers ─────────────────────────────────────────────
    application.add_handler(CallbackQueryHandler(handle_cancel, pattern=r'^(cancel|cancel_schedule)$'))
    application.add_handler(CallbackQueryHandler(handle_approve, pattern=r'^approve_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_reject,  pattern=r'^reject_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_unblock_callback, pattern=r'^unblock_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_location_type, pattern='^loc_(campus|rocketchat)$'))
    application.add_handler(CallbackQueryHandler(handle_admin_menu, pattern='^admin_menu$'))
    application.add_handler(CallbackQueryHandler(handle_view_employees, pattern='^admin_view_employees$'))
    application.add_handler(CallbackQueryHandler(handle_remove_employee_list, pattern='^admin_remove_employee$'))
    application.add_handler(CallbackQueryHandler(handle_remove_employee_confirm_prompt, pattern=r'^remove_user_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_remove_employee_execute, pattern=r'^confirm_rm_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_view_schedules, pattern='^admin_view_schedules$'))
    application.add_handler(CallbackQueryHandler(handle_view_rejected, pattern='^admin_view_rejected$'))

    # Weekly schedule non-text action callbacks
    application.add_handler(CallbackQueryHandler(handle_weekly_schedule_employees_list, pattern='^(admin_weekly_schedule|admin_add_schedule)$'))
    application.add_handler(CallbackQueryHandler(handle_schedule_user_menu, pattern=r'^sched_user_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_sched_days_view, pattern=r'^sched_days_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_sched_edit_single_day, pattern=r'^sched_editday_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_sched_dayoff, pattern=r'^sched_dayoff_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_sched_clear_confirm, pattern=r'^sched_clear_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_sched_clear_execute, pattern=r'^confirm_clear_sched_\d+$'))

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
