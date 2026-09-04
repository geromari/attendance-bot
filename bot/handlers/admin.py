from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from bot.services.attendance import attendance_service
from bot.services.schedule import schedule_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from ..config import config
from datetime import time
from bot.models.user import User

# Admin conversation states
WAITING_NICKNAME_FOR_SCHEDULE = 1
WAITING_DAY = 2
WAITING_START_TIME = 3
WAITING_END_TIME = 4

DAY_NAMES = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba']
DAY_NAMES_SHORT = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']


async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu — works from reply keyboard (message) or inline callback"""
    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        text = "❌ Ruxsat yo'q. Faqat adminlar uchun."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    text = "🔧 **Admin panel**\n\nAmalni tanlang:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode='Markdown', reply_markup=keyboards.admin_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode='Markdown', reply_markup=keyboards.admin_menu()
        )



async def handle_add_schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add schedule conversation"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Ruxsat yo'q. Faqat adminlar uchun.",
            reply_markup=keyboards.back_to_main()
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ **Jadval qo'shish**\n\n"
        "Xodimning taxallusini kiriting:",
        parse_mode='Markdown',
        reply_markup=keyboards.cancel_action()
    )

    return WAITING_NICKNAME_FOR_SCHEDULE


async def receive_nickname_for_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive nickname for schedule setup"""
    nickname = update.message.text.strip()

    async with async_session() as session:
        user = await attendance_service.get_user_by_nickname(session, nickname)

        if not user:
            await update.message.reply_text(
                f"❌ '{nickname}' taxallusli xodim topilmadi.\n\n"
                f"Iltimos, to'g'ri taxallus kiriting:",
                reply_markup=keyboards.cancel_action()
            )
            return WAITING_NICKNAME_FOR_SCHEDULE

        context.user_data['schedule_user_id'] = user.id
        context.user_data['schedule_user_nickname'] = nickname

        await update.message.reply_text(
            f"✅ Xodim: {nickname}\n\n"
            f"Kunni tanlang:",
            reply_markup=keyboards.day_selection()
        )

        return WAITING_DAY


async def receive_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive day selection for schedule"""
    query = update.callback_query
    await query.answer()

    day_data = query.data  # day_0, day_1, etc.
    day_of_week = int(day_data.split('_')[1])

    context.user_data['schedule_day'] = day_of_week

    await query.edit_message_text(
        f"✅ Kun: {DAY_NAMES[day_of_week]}\n\n"
        f"Boshlanish vaqtini kiriting (HH:MM formatida, masalan 09:00):",
        reply_markup=keyboards.cancel_action()
    )

    return WAITING_START_TIME


async def receive_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive start time for schedule"""
    time_str = update.message.text.strip()

    try:
        hours, minutes = map(int, time_str.split(':'))
        start_time = time(hours, minutes)
        context.user_data['schedule_start_time'] = start_time

        await update.message.reply_text(
            f"✅ Boshlanish vaqti: {start_time.strftime('%H:%M')}\n\n"
            f"Tugash vaqtini kiriting (HH:MM formatida, masalan 17:00):",
            reply_markup=keyboards.cancel_action()
        )

        return WAITING_END_TIME

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Noto'g'ri vaqt formati. HH:MM formatida kiriting (masalan, 09:00):",
            reply_markup=keyboards.cancel_action()
        )
        return WAITING_START_TIME


async def receive_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive end time and save schedule"""
    time_str = update.message.text.strip()

    try:
        hours, minutes = map(int, time_str.split(':'))
        end_time = time(hours, minutes)

        user_id = context.user_data['schedule_user_id']
        day_of_week = context.user_data['schedule_day']
        start_time = context.user_data['schedule_start_time']
        nickname = context.user_data['schedule_user_nickname']

        async with async_session() as session:
            # Get user object
            user = await session.get(User, user_id)
            if user:
                schedule = await schedule_service.set_schedule(
                    session, user, day_of_week, start_time, end_time
                )

                await update.message.reply_text(
                    f"✅ Jadval muvaffaqiyatli saqlandi!\n\n"
                    f"Xodim: {nickname}\n"
                    f"Kun: {DAY_NAMES[day_of_week]}\n"
                    f"Vaqt: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                    reply_markup=keyboards.admin_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ Xato: Foydalanuvchi topilmadi.",
                    reply_markup=keyboards.admin_menu()
                )

        # Clear context
        context.user_data.clear()

        return ConversationHandler.END

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Noto'g'ri vaqt formati. HH:MM formatida kiriting (masalan, 17:00):",
            reply_markup=keyboards.cancel_action()
        )
        return WAITING_END_TIME


async def handle_view_employees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view all employees button"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Ruxsat yo'q. Faqat adminlar uchun.",
            reply_markup=keyboards.back_to_main()
        )
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await query.edit_message_text(
                "👥 **Barcha xodimlar**\n\n"
                "Hali hech kim ro'yxatdan o'tmagan.",
                parse_mode='Markdown',
                reply_markup=keyboards.admin_menu()
            )
            return

        text = "👥 **Barcha xodimlar**\n\n"
        for user in users:
            admin_badge = " 👑" if user.is_admin else ""
            text += f"• {user.nickname}{admin_badge}\n"

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.admin_menu()
        )


async def handle_view_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view all schedules button"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Ruxsat yo'q. Faqat adminlar uchun.",
            reply_markup=keyboards.back_to_main()
        )
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await query.edit_message_text(
                "📋 **Xodimlar jadvali**\n\n"
                "Hali hech kim ro'yxatdan o'tmagan.",
                parse_mode='Markdown',
                reply_markup=keyboards.admin_menu()
            )
            return

        text = "📋 **Xodimlar jadvali**\n\n"

        for user in users:
            schedules = await schedule_service.get_user_schedule(session, user)

            if schedules:
                text += f"**{user.nickname}:**\n"
                for schedule in schedules:
                    text += f"  {DAY_NAMES_SHORT[schedule.day_of_week]}: "
                    text += f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}\n"
            else:
                text += f"**{user.nickname}:** Jadval belgilanmagan\n"

            text += "\n"

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.admin_menu()
        )
