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


async def handle_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Leaderboard button press"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        is_admin = user.is_admin if user else False

        leaderboard = await attendance_service.get_all_users_with_week_hours(session)

        if not leaderboard:
            await update.message.reply_text(
                "🏆 **Leaderboard**\n\nNo employees registered yet.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu(is_admin=is_admin)
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        text = "🏆 **Leaderboard**\n\nTop employees this week:\n\n"

        for idx, (u, hours) in enumerate(leaderboard[:10], 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."
            text += f"{medal} **{u.nickname}** — {_fmt_duration(hours)}\n"

        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=is_admin)
        )
