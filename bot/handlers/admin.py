from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from bot.services.attendance import attendance_service
from bot.services.schedule import schedule_service
from bot.keyboards.inline import (
    keyboards, BTN_CHECKIN, BTN_CHECKOUT, BTN_PROFILE,
    BTN_LEADERBOARD, BTN_ANONYMOUS, BTN_ADMIN
)
from database.db import async_session
from bot.config import config
from datetime import time
from bot.models.user import User
from bot.utils.helpers import parse_time_range

# Weekly schedule conversation states
WAITING_SCHED_NICKNAME = 1
WAITING_SCHED_PRESET_TIME = 2
WAITING_SCHED_FULL_TEXT = 3
WAITING_SCHED_SINGLE_DAY_TIME = 4

# Backward compatibility aliases
WAITING_NICKNAME_FOR_SCHEDULE = WAITING_SCHED_NICKNAME
WAITING_DAY = 20
WAITING_START_TIME = 21
WAITING_END_TIME = 22

DAY_NAMES = [
    'Dushanba (Mon)', 'Seshanba (Tue)', 'Chorshanba (Wed)',
    'Payshanba (Thu)', 'Juma (Fri)', 'Shanba (Sat)', 'Yakshanba (Sun)'
]
DAY_NAMES_SHORT = ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak']


async def check_and_handle_intercept(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Check if user text is a navigation command, bottom reply button, or cancel word"""
    clean = text.strip()
    clean_lower = clean.lower()

    if clean_lower in ['cancel', '/cancel', 'bekor', 'bekor qilish', 'ortga', 'chiqish', 'stop', 'exit']:
        await handle_schedule_cancel(update, context)
        return True

    if clean == BTN_ADMIN or clean == '/admin':
        context.user_data.clear()
        await handle_admin_menu(update, context)
        return True

    if clean == BTN_CHECKIN:
        context.user_data.clear()
        from bot.handlers.checkin import handle_checkin
        await handle_checkin(update, context)
        return True

    if clean == BTN_CHECKOUT:
        context.user_data.clear()
        from bot.handlers.checkin import handle_checkout
        await handle_checkout(update, context)
        return True

    if clean == BTN_PROFILE:
        context.user_data.clear()
        from bot.handlers.profile import handle_profile
        await handle_profile(update, context)
        return True

    if clean == BTN_LEADERBOARD:
        context.user_data.clear()
        from bot.handlers.leaderboard import handle_leaderboard
        await handle_leaderboard(update, context)
        return True

    if clean == BTN_ANONYMOUS or clean == '/anonymous':
        context.user_data.clear()
        from bot.handlers.anonymous import start_anonymous_message
        await start_anonymous_message(update, context)
        return True

    return False


async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu — works from reply keyboard (message) or inline callback"""
    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        text = "❌ Access denied. For admins only."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    text = "🔧 **Admin Panel**\n\nChoose an action:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode='Markdown', reply_markup=keyboards.admin_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode='Markdown', reply_markup=keyboards.admin_menu()
        )


async def _render_user_schedule_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Render employee's weekly schedule overview and action buttons"""
    async with async_session() as session:
        schedules = await schedule_service.get_user_schedule(session, user)
        sched_dict = {s.day_of_week: s for s in schedules}

    text = f"🗓 **{user.nickname} ning haftalik ish jadvali**\n"
    if user.full_name:
        text += f"👤 *{user.full_name}*\n"
    text += "\n**Joriy jadval:**\n"

    for day_num, day_name in enumerate(DAY_NAMES):
        if day_num in sched_dict:
            s = sched_dict[day_num]
            text += f"• **{day_name}:** `{s.start_time.strftime('%H:%M')} — {s.end_time.strftime('%H:%M')}`\n"
        else:
            text += f"• **{day_name}:** 🏖 *Dam olish kuni*\n"

    text += "\nQuyidagi variantlardan birini tanlang:"
    markup = keyboards.schedule_mode_menu(user.id)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)


async def handle_weekly_schedule_employees_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of employees to set/view weekly schedule"""
    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("❌ Access denied!", show_alert=True)
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()

    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.nickname))
        users = result.scalars().all()

        if not users:
            text = "👥 **Haftalik ish jadvali**\n\nTizimda hali birorta ham xodim mavjud emas."
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboards.back_to_main())
            else:
                await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboards.back_to_main())
            return ConversationHandler.END

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        for u in users:
            label = f"👤 {u.nickname}"
            if u.full_name:
                label += f" ({u.full_name})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"sched_user_{u.id}")])

        buttons.append([InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="admin_menu")])

        text = (
            "🗓 **Haftalik ish jadvalini boshqarish**\n\n"
            "Jadvalini belgilamoqchi bo'lgan xodimni tanlang:\n"
            "*(yoki xodim taxallusini yozib yuborishingiz mumkin)*"
        )

        markup = InlineKeyboardMarkup(buttons)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)

    return WAITING_SCHED_NICKNAME


async def receive_sched_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle nickname typed as text when selecting employee for schedule"""
    text = update.message.text.strip()
    if await check_and_handle_intercept(update, context, text):
        return ConversationHandler.END

    nickname = text
    async with async_session() as session:
        user = await attendance_service.get_user_by_nickname(session, nickname)
        if not user:
            await update.message.reply_text(
                f"❌ '{nickname}' taxallusli xodim topilmadi.\n\n"
                f"Iltimos, qaytadan kiriting:",
                reply_markup=keyboards.cancel_action()
            )
            return WAITING_SCHED_NICKNAME

    await _render_user_schedule_menu(update, context, user)
    return ConversationHandler.END


async def handle_schedule_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback when clicking on an employee to configure schedule"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return ConversationHandler.END

    user_id = int(query.data.split('_')[-1])
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text("❌ Xodim topilmadi.", reply_markup=keyboards.back_to_main())
            return ConversationHandler.END

    await _render_user_schedule_menu(update, context, user)
    return ConversationHandler.END


async def handle_sched_preset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for time range for preset (Mon-Fri, Mon-Sat, All days)"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return ConversationHandler.END

    parts = query.data.split('_')
    preset_type = int(parts[2])  # 5, 6, 7
    user_id = int(parts[3])

    context.user_data['sched_user_id'] = user_id
    context.user_data['sched_preset_type'] = preset_type

    names = {
        5: "Dushanba — Juma (Mon-Fri)",
        6: "Dushanba — Shanba (Mon-Sat)",
        7: "Har kuni (7 kun / All days)"
    }

    text = (
        f"⚡️ **{names[preset_type]} uchun ish vaqtini kiriting**\n\n"
        f"Format: `BOSHLANISH - TUGASH`\n"
        f"Misollar:\n"
        f"• `09:00 - 18:00`\n"
        f"• `12:00 - 18:00`\n"
        f"• `10:00 19:00`\n\n"
        f"Iltimos, ish vaqtini yuboring:"
    )

    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboards.schedule_cancel_action(user_id)
    )
    return WAITING_SCHED_PRESET_TIME


async def receive_sched_preset_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive time range and apply to preset days"""
    time_text = update.message.text.strip()
    if await check_and_handle_intercept(update, context, time_text):
        return ConversationHandler.END

    times = parse_time_range(time_text)

    user_id = context.user_data.get('sched_user_id')
    preset_type = context.user_data.get('sched_preset_type', 5)

    if not times:
        await update.message.reply_text(
            "❌ **Noto'g'ri vaqt formati!**\n\n"
            "Iltimos, vaqtni `09:00 - 18:00` yoki `12:00-18:00` ko'rinishida kiriting\n"
            "*(yoki bekor qilish uchun pastdagi tugmani bosing)*:",
            parse_mode='Markdown',
            reply_markup=keyboards.schedule_cancel_action(user_id) if user_id else keyboards.cancel_action()
        )
        return WAITING_SCHED_PRESET_TIME

    start_time, end_time = times
    days = list(range(preset_type))

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("❌ Xodim topilmadi.", reply_markup=keyboards.admin_menu())
            context.user_data.clear()
            return ConversationHandler.END

        await schedule_service.set_bulk_days_schedule(
            session, user, days, start_time, end_time, clear_others=True
        )

    names = {
        5: "Dushanba — Juma (Shanba va Yakshanba: Dam olish)",
        6: "Dushanba — Shanba (Yakshanba: Dam olish)",
        7: "Har kuni (7 kun)"
    }

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 Boshqa xodimga jadval", callback_data="admin_weekly_schedule")],
        [InlineKeyboardButton("🏠 Admin Menyu", callback_data="admin_menu")],
    ])

    await update.message.reply_text(
        f"✅ **Haftalik ish jadvali muvaffaqiyatli saqlandi!**\n\n"
        f"👤 Xodim: **{user.nickname}**\n"
        f"📅 Kunlar: **{names.get(preset_type)}**\n"
        f"⏰ Ish vaqti: `{start_time.strftime('%H:%M')} — {end_time.strftime('%H:%M')}`",
        parse_mode='Markdown',
        reply_markup=markup
    )

    context.user_data.clear()
    return ConversationHandler.END


async def handle_sched_text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for pasting all 7 days in one message"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return ConversationHandler.END

    user_id = int(query.data.split('_')[-1])
    context.user_data['sched_user_id'] = user_id

    text = (
        "✍️ **Bir haftalik jadvalni matn orqali kiritish**\n\n"
        "Har bir kun uchun vaqtni yangi qatordan yuboring. Dam olish kuni uchun `dam` yoki `off` deb yozing:\n\n"
        "**Namuna:**\n"
        "```\n"
        "1. 09:00 - 18:00\n"
        "2. 09:00 - 18:00\n"
        "3. 09:00 - 18:00\n"
        "4. 09:00 - 18:00\n"
        "5. 09:00 - 18:00\n"
        "6. 10:00 - 15:00\n"
        "7. dam\n"
        "```\n"
        "*(1=Dush, 2=Sesh, 3=Chor, 4=Pay, 5=Jum, 6=Shan, 7=Yak)*\n\n"
        "Iltimos, jadval matnini yuboring:"
    )

    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboards.schedule_cancel_action(user_id)
    )
    return WAITING_SCHED_FULL_TEXT


async def receive_sched_full_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse multiline weekly schedule and save"""
    text = update.message.text.strip()
    if await check_and_handle_intercept(update, context, text):
        return ConversationHandler.END

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    user_id = context.user_data.get('sched_user_id')

    if not lines:
        await update.message.reply_text("❌ Matn bo'sh. Iltimos, qaytadan yuboring:")
        return WAITING_SCHED_FULL_TEXT

    sched_dict = {}
    for idx, line in enumerate(lines[:7]):
        is_off = any(w in line.lower() for w in ['dam', 'off', 'yoq', 'none', 'holiday', 'rest'])
        if is_off:
            sched_dict[idx] = None
        else:
            times = parse_time_range(line)
            if times:
                sched_dict[idx] = times
            else:
                sched_dict[idx] = None

    if not sched_dict:
        await update.message.reply_text(
            "❌ Jadval tushunarsiz formatda. Iltimos namunadagidek yuboring:\n"
            "`1. 09:00 - 18:00`\n`2. 09:00 - 18:00`...",
            parse_mode='Markdown',
            reply_markup=keyboards.schedule_cancel_action(user_id) if user_id else keyboards.cancel_action()
        )
        return WAITING_SCHED_FULL_TEXT

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("❌ Xodim topilmadi.", reply_markup=keyboards.admin_menu())
            context.user_data.clear()
            return ConversationHandler.END

        await schedule_service.set_weekly_schedule(session, user, sched_dict)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 Boshqa xodimga jadval", callback_data="admin_weekly_schedule")],
        [InlineKeyboardButton("🏠 Admin Menyu", callback_data="admin_menu")],
    ])

    await update.message.reply_text(
        f"✅ **{user.nickname} ning 7 kunlik jadvali muvaffaqiyatli saqlandi!**",
        parse_mode='Markdown',
        reply_markup=markup
    )

    context.user_data.clear()
    return ConversationHandler.END


async def handle_sched_days_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show 7 days menu for manual day-by-day adjustment"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[-1])
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text("❌ Xodim topilmadi.", reply_markup=keyboards.back_to_main())
            return ConversationHandler.END

        schedules = await schedule_service.get_user_schedule(session, user)
        sched_dict = {s.day_of_week: s for s in schedules}

    text = f"📅 **{user.nickname} — Kunma-kun to'g'irlash**\n\nO'zgartirmoqchi bo'lgan kuningizni tanlang:"
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboards.schedule_days_menu(user_id, sched_dict)
    )
    return ConversationHandler.END


async def handle_sched_edit_single_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show action options for a single day"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    user_id = int(parts[2])
    day_num = int(parts[3])

    async with async_session() as session:
        user = await session.get(User, user_id)
        schedules = await schedule_service.get_user_schedule(session, user)
        sched_dict = {s.day_of_week: s for s in schedules}

    has_schedule = day_num in sched_dict
    status = f"`{sched_dict[day_num].start_time.strftime('%H:%M')} — {sched_dict[day_num].end_time.strftime('%H:%M')}`" if has_schedule else "Dam olish"

    text = f"📅 **{DAY_NAMES[day_num]}**\n\nJoriy holat: {status}\n\nAmalni tanlang:"
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboards.schedule_day_action(user_id, day_num, has_schedule)
    )
    return ConversationHandler.END


async def handle_sched_dayoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a day as day off"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    user_id = int(parts[2])
    day_num = int(parts[3])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            await schedule_service.delete_schedule(session, user, day_num)
            schedules = await schedule_service.get_user_schedule(session, user)
            sched_dict = {s.day_of_week: s for s in schedules}
            text = f"📅 **{user.nickname} — Kunma-kun to'g'irlash**\n\n✅ {DAY_NAMES[day_num]} dam olish kuni deb belgilandi."
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=keyboards.schedule_days_menu(user_id, sched_dict)
            )
    return ConversationHandler.END


async def handle_sched_input_single_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for time input for a single day"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    user_id = int(parts[2])
    day_num = int(parts[3])

    context.user_data['sched_user_id'] = user_id
    context.user_data['sched_single_day'] = day_num

    text = (
        f"⏱ **{DAY_NAMES[day_num]} uchun ish vaqtini kiriting**\n\n"
        f"Format: `09:00 - 18:00` yoki `12:00 - 18:00`\n\n"
        f"Iltimos, vaqtni yuboring:"
    )

    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboards.schedule_single_day_cancel_action(user_id)
    )
    return WAITING_SCHED_SINGLE_DAY_TIME


async def receive_sched_single_day_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive time for a single day and save"""
    time_text = update.message.text.strip()
    if await check_and_handle_intercept(update, context, time_text):
        return ConversationHandler.END

    times = parse_time_range(time_text)

    user_id = context.user_data.get('sched_user_id')
    day_num = context.user_data.get('sched_single_day')

    if not times:
        await update.message.reply_text(
            "❌ **Noto'g'ri vaqt formati!**\n\n"
            "Iltimos, vaqtni `09:00 - 18:00` yoki `12:00-18:00` ko'rinishida kiriting\n"
            "*(yoki bekor qilish uchun pastdagi tugmani bosing)*:",
            parse_mode='Markdown',
            reply_markup=keyboards.schedule_single_day_cancel_action(user_id) if user_id else keyboards.cancel_action()
        )
        return WAITING_SCHED_SINGLE_DAY_TIME

    start_time, end_time = times
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            await schedule_service.set_schedule(session, user, day_num, start_time, end_time)

    await update.message.reply_text(
        f"✅ **{DAY_NAMES[day_num]}** uchun ish vaqti `{start_time.strftime('%H:%M')} — {end_time.strftime('%H:%M')}` qilib saqlandi!"
    )
    if user:
        await _render_user_schedule_menu(update, context, user)

    context.user_data.clear()
    return ConversationHandler.END


async def handle_sched_clear_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask confirmation to clear all schedules"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[-1])
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text("❌ Xodim topilmadi.", reply_markup=keyboards.back_to_main())
            return ConversationHandler.END

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Ha, barchasini o'chirish", callback_data=f"confirm_clear_sched_{user_id}")],
        [InlineKeyboardButton("⬅️ Bekor qilish", callback_data=f"sched_user_{user_id}")]
    ])

    await query.edit_message_text(
        f"⚠️ **Diqqat!**\n\n**{user.nickname}** ning barcha kunlardagi ish jadvallarini o'chirmoqchimisiz?",
        parse_mode='Markdown',
        reply_markup=markup
    )
    return ConversationHandler.END


async def handle_sched_clear_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute clearing all schedules for user"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[-1])
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            await schedule_service.clear_all_user_schedules(session, user)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 Qayta jadval belgilash", callback_data=f"sched_user_{user_id}")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="admin_menu")]
    ])

    await query.edit_message_text(
        f"✅ **{user.nickname}** ning barcha ish jadvallari o'chirildi.",
        parse_mode='Markdown',
        reply_markup=markup
    )
    return ConversationHandler.END


async def handle_setschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /setschedule <nickname> <start_time>-<end_time> [mon-sat|all]"""
    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📋 **Ishlatish:** `/setschedule <nickname> <start_time>-<end_time> [mon-sat|all]`\n\n"
            "**Misollar:**\n"
            "• `/setschedule john 12:00-18:00` *(Dushanba-Juma)*\n"
            "• `/setschedule john 09:00-18:00 mon-sat` *(Dushanba-Shanba)*\n"
            "• `/setschedule john 10:00-20:00 all` *(Har kuni)*",
            parse_mode='Markdown'
        )
        return

    nickname = context.args[0].strip()
    time_arg = context.args[1].strip()
    mode_arg = context.args[2].lower() if len(context.args) > 2 else "mon-fri"

    times = parse_time_range(time_arg)
    if not times:
        await update.message.reply_text("❌ Noto'g'ri vaqt formati. Misol: `12:00-18:00`", parse_mode='Markdown')
        return

    start_time, end_time = times
    if "sat" in mode_arg or "6" in mode_arg:
        days = list(range(6))
        day_label = "Dushanba — Shanba"
    elif "all" in mode_arg or "7" in mode_arg:
        days = list(range(7))
        day_label = "Har kuni (7 kun)"
    else:
        days = list(range(5))
        day_label = "Dushanba — Juma"

    async with async_session() as session:
        user = await attendance_service.get_user_by_nickname(session, nickname)
        if not user:
            await update.message.reply_text(f"❌ '{nickname}' taxallusli xodim topilmadi.")
            return

        await schedule_service.set_bulk_days_schedule(session, user, days, start_time, end_time, clear_others=True)

    await update.message.reply_text(
        f"✅ **Haftalik jadval muvaffaqiyatli saqlandi!**\n\n"
        f"👤 Xodim: **{user.nickname}**\n"
        f"📅 Kunlar: **{day_label}**\n"
        f"⏰ Ish vaqti: `{start_time.strftime('%H:%M')} — {end_time.strftime('%H:%M')}`",
        parse_mode='Markdown'
    )


async def handle_schedule_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel schedule conversation"""
    context.user_data.clear()
    text = "❌ **Jadval kiritish bekor qilindi.**\n\nQuyidagi amallardan birini tanlang:"
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=keyboards.admin_menu()
            )
        except Exception:
            await update.callback_query.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=keyboards.admin_menu()
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.admin_menu()
        )
    return ConversationHandler.END


# Backward compatibility aliases
handle_add_schedule_start = handle_weekly_schedule_employees_list
receive_nickname_for_schedule = receive_sched_nickname
receive_day = handle_schedule_user_menu
receive_start_time = receive_sched_preset_time
receive_end_time = receive_sched_single_day_time


async def handle_view_employees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view all employees button"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Access denied. For admins only.",
            reply_markup=keyboards.back_to_main()
        )
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await query.edit_message_text(
                "👥 **All Employees**\n\n"
                "No employees registered yet.",
                parse_mode='Markdown',
                reply_markup=keyboards.back_to_main()
            )
            return

        text = "👥 **All Employees**\n\n"
        for user in users:
            admin_badge = " 👑" if user.is_admin else ""
            name_info = f" ({user.full_name})" if user.full_name else ""
            text += f"• **{user.nickname}**{name_info}{admin_badge} — ID: `{user.telegram_id}`\n"

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [
            [InlineKeyboardButton("🗑 Remove Employee", callback_data="admin_remove_employee")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_menu")]
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def handle_view_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view all schedules button"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Access denied. For admins only.",
            reply_markup=keyboards.back_to_main()
        )
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await query.edit_message_text(
                "📋 **Employee Schedules**\n\n"
                "No employees registered yet.",
                parse_mode='Markdown',
                reply_markup=keyboards.back_to_main()
            )
            return

        text = "📋 **Employee Schedules**\n\n"

        for user in users:
            schedules = await schedule_service.get_user_schedule(session, user)

            if schedules:
                text += f"**{user.nickname}:**\n"
                for schedule in schedules:
                    text += f"  {DAY_NAMES_SHORT[schedule.day_of_week]}: "
                    text += f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}\n"
            else:
                text += f"**{user.nickname}:** No schedule set\n"

            text += "\n"

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.back_to_main()
        )


async def handle_view_rejected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view rejected employee requests"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Access denied. For admins only.",
            reply_markup=keyboards.back_to_main()
        )
        return

    async with async_session() as session:
        rejected_list = await attendance_service.get_all_rejected_requests(session)

        if not rejected_list:
            await query.edit_message_text(
                "🚫 **Rejected Requests**\n\n"
                "There are currently no rejected requests.",
                parse_mode='Markdown',
                reply_markup=keyboards.back_to_main()
            )
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        text = "🚫 **Rejected Requests**\n\n"
        buttons = []
        for req in rejected_list:
            text += f"• **{req.nickname}** ({req.full_name or 'No name'}) — ID: `{req.telegram_id}`\n"
            buttons.append([InlineKeyboardButton(f"🔄 Unblock {req.nickname}", callback_data=f"unblock_{req.telegram_id}")])

        buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_menu")])

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def handle_unreject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command /unreject <telegram_id> to allow a rejected user to register again"""
    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("Usage: `/unreject <telegram_id>`", parse_mode='Markdown')
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid Telegram ID. Must be numeric.")
        return

    async with async_session() as session:
        deleted = await attendance_service.delete_registration_request(session, target_id)
        if deleted:
            await update.message.reply_text(
                f"✅ User `{target_id}` has been unblocked. They can now send /start to register again.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ No rejected request found for Telegram ID `{target_id}`.",
                parse_mode='Markdown'
            )


async def handle_unblock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query to unblock a rejected user"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    target_id = int(query.data.split('_')[1])
    async with async_session() as session:
        await attendance_service.delete_registration_request(session, target_id)

    await query.edit_message_text(
        f"✅ User `{target_id}` has been unblocked. They can now send /start to register again.",
        parse_mode='Markdown',
        reply_markup=keyboards.back_to_main()
    )


async def handle_remove_employee_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of employees that can be removed"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        removable_users = [u for u in users if not u.is_admin and u.telegram_id not in config.ADMIN_IDS]

        if not removable_users:
            await query.edit_message_text(
                "🗑 **Remove Employee**\n\nNo removable employees found in the system.",
                parse_mode='Markdown',
                reply_markup=keyboards.back_to_main()
            )
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        text = "🗑 **Remove Employee**\n\nSelect an employee to remove from the system:"
        buttons = []
        for user in removable_users:
            label = f"❌ {user.nickname}"
            if user.full_name:
                label += f" ({user.full_name})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"remove_user_{user.id}")])

        buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_menu")])

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def handle_remove_employee_confirm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask confirmation before removing an employee"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    user_id = int(query.data.split('_')[-1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text(
                "❌ Employee not found.",
                reply_markup=keyboards.back_to_main()
            )
            return

        if user.is_admin or user.telegram_id in config.ADMIN_IDS:
            await query.answer("❌ Administrators cannot be removed!", show_alert=True)
            return

        text = (
            f"⚠️ **Confirm Employee Removal**\n\n"
            f"Are you sure you want to remove employee **{user.nickname}**?\n\n"
            f"• Full name: {user.full_name or 'N/A'}\n"
            f"• Telegram ID: `{user.telegram_id}`\n\n"
            f"🚨 **Warning:** This will delete all their schedules, check-in history, and block access to the bot."
        )

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboards.remove_employee_confirm(user.id)
        )


async def handle_remove_employee_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute removal of employee"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    user_id = int(query.data.split('_')[-1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text(
                "❌ Employee not found or already removed.",
                reply_markup=keyboards.back_to_main()
            )
            return

        if user.is_admin or user.telegram_id in config.ADMIN_IDS:
            await query.answer("❌ Administrators cannot be removed!", show_alert=True)
            return

        target_telegram_id = user.telegram_id
        nickname = user.nickname

        await attendance_service.remove_user(session, user.id, mark_as_rejected=True)

    # Notify employee if possible
    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=(
                "⚠️ **Notification**\n\n"
                "You have been removed from the employee system by an administrator.\n"
                "You no longer have access to attendance features."
            ),
            parse_mode='Markdown',
            reply_markup=keyboards.remove()
        )
    except Exception:
        pass

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Remove Another", callback_data="admin_remove_employee")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_menu")],
    ])

    await query.edit_message_text(
        f"✅ Employee **{nickname}** (`{target_telegram_id}`) has been successfully removed and blocked.",
        parse_mode='Markdown',
        reply_markup=markup
    )


async def handle_remove_employee_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command /remove or /fire <nickname> to remove an employee"""
    telegram_id = update.effective_user.id
    if telegram_id not in config.ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/remove <nickname>` or `/fire <nickname>`",
            parse_mode='Markdown'
        )
        return

    nickname = context.args[0].strip()

    async with async_session() as session:
        user = await attendance_service.get_user_by_nickname(session, nickname)
        if not user:
            await update.message.reply_text(f"❌ Employee with nickname '{nickname}' not found.")
            return

        if user.is_admin or user.telegram_id in config.ADMIN_IDS:
            await update.message.reply_text("❌ Administrators cannot be removed.")
            return

        target_telegram_id = user.telegram_id
        await attendance_service.remove_user(session, user.id, mark_as_rejected=True)

    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=(
                "⚠️ **Notification**\n\n"
                "You have been removed from the employee system by an administrator.\n"
                "You no longer have access to attendance features."
            ),
            parse_mode='Markdown',
            reply_markup=keyboards.remove()
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ Employee **{nickname}** (`{target_telegram_id}`) has been successfully removed and blocked.",
        parse_mode='Markdown'
    )

