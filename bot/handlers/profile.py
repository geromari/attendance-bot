from telegram import Update
from telegram.ext import ContextTypes
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session

DAY_NAMES_UZ = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba']


def _fmt_duration(hours: float) -> str:
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f"{h} soat {m} daqiqa"
    elif h:
        return f"{h} soat"
    else:
        return f"{m} daqiqa"


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle My Profile button press"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Foydalanuvchi topilmadi. /start buyrug'i orqali ro'yxatdan o'ting.",
                reply_markup=keyboards.main_menu()
            )
            return

        week_hours = await attendance_service.get_week_hours(session, user)
        days_worked = await attendance_service.get_week_days_worked(session, user)
        days_count = len(days_worked)

        days_str = (
            "\n".join([f"  • {day}" for day in days_worked])
            if days_worked else "  • Hali ish kunlari yo'q"
        )

        profile_text = (
            f"👤 **Mening profilim**\n\n"
            f"📛 Taxallus: {user.nickname}\n"
            f"{'👑 Admin' if user.is_admin else '👤 Xodim'}\n\n"
            f"📊 **Bu haftaning statistikasi**\n\n"
            f"⏱️ Jami vaqt: {_fmt_duration(week_hours)}\n"
            f"📅 Ish kunlari: {days_count} kun\n"
            f"📍 Kunlar:\n{days_str}\n"
        )

        await update.message.reply_text(
            profile_text,
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=user.is_admin)
        )
