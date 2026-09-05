from telegram import Update
from telegram.ext import ContextTypes
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session


def _fmt_duration(hours: float) -> str:
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f"{h}h {m}m"
    elif h:
        return f"{h}h"
    else:
        return f"{m}m"


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle My Profile button press"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ User not found. Please register by sending /start.",
                reply_markup=keyboards.main_menu()
            )
            return

        week_hours = await attendance_service.get_week_hours(session, user)
        days_worked = await attendance_service.get_week_days_worked(session, user)
        days_count = len(days_worked)

        days_str = (
            "\n".join([f"  • {day}" for day in days_worked])
            if days_worked else "  • No working days yet"
        )

        profile_text = (
            f"👤 **My Profile**\n\n"
            f"📛 Nickname: {user.nickname}\n"
            f"{'👑 Admin' if user.is_admin else '👤 Employee'}\n\n"
            f"📊 **This Week's Statistics**\n\n"
            f"⏱️ Total time: {_fmt_duration(week_hours)}\n"
            f"📅 Days worked: {days_count} days\n"
            f"📍 Days:\n{days_str}\n"
        )

        await update.message.reply_text(
            profile_text,
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=user.is_admin)
        )
