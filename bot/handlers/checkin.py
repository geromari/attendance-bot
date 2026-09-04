from telegram import Update
from telegram.ext import ContextTypes
from bot.services.attendance import attendance_service
from bot.services.location import location_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from ..config import config


def _fmt_duration(hours: float) -> str:
    """Format duration as 'X soat Y daqiqa'"""
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f"{h} soat {m} daqiqa"
    elif h:
        return f"{h} soat"
    else:
        return f"{m} daqiqa"


# ─── Reply keyboard button handler ───────────────────────────────────────────

async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: User pressed Kirish — ask which location type"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Avval ro'yxatdan o'ting. /start buyrug'ini yuboring."
            )
            return

        # Already checked in?
        active_checkin = await attendance_service.get_active_checkin(session, user)
        if active_checkin:
            await update.message.reply_text(
                "⚠️ Siz allaqachon kirishni amalga oshirgansiz.\n"
                "Avval chiqishni amalga oshiring.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return

        # Daily limit reached?
        today_hours = await attendance_service.get_today_hours(session, user)
        if today_hours >= config.DAILY_HOUR_LIMIT:
            await update.message.reply_text(
                f"😴 Sizning kunlik limitingiz tugadi, dam oling!\n\n"
                f"Bugungi ishlangan vaqt: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return

    # Ask location type
    await update.message.reply_text(
        "🏢 Qaysi joydan ishlayapsiz?",
        reply_markup=keyboards.location_type()
    )


async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checkout directly without location"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Avval ro'yxatdan o'ting. /start buyrug'ini yuboring."
            )
            return

        active_checkin = await attendance_service.get_active_checkin(session, user)
        if not active_checkin:
            await update.message.reply_text(
                "⚠️ Faol kirish topilmadi.\nAvval kirishni amalga oshiring.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return

        attendance = await attendance_service.check_out(
            session, user, None, None, is_auto=False
        )

        if attendance:
            duration = attendance.duration_hours
            today_hours = await attendance_service.get_today_hours(session, user)
            ci = attendance.check_in_time
            co = attendance.check_out_time

            await update.message.reply_text(
                f"✅ Chiqish muvaffaqiyatli! Yaxshi kun! 🌟\n\n"
                f"🕐 Kirish: {ci.hour:02d}:{ci.minute:02d}\n"
                f"🕐 Chiqish: {co.hour:02d}:{co.minute:02d}\n"
                f"⏱️ Sessiya: {_fmt_duration(duration)}\n"
                f"📊 Bugun jami: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
        else:
            await update.message.reply_text(
                "❌ Faol kirish topilmadi.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )


# ─── Inline callback: location type selected ─────────────────────────────────

async def handle_location_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: User chose Campus or Rocketchat"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    choice = query.data  # "loc_campus" or "loc_rocketchat"

    if choice == "loc_rocketchat":
        # No location needed — check in immediately
        async with async_session() as session:
            user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

            # Guard: re-check limit (race condition)
            today_hours = await attendance_service.get_today_hours(session, user)
            if today_hours >= config.DAILY_HOUR_LIMIT:
                await query.edit_message_text(
                    f"😴 Sizning kunlik limitingiz tugadi, dam oling!\n\n"
                    f"Bugungi ishlangan vaqt: {_fmt_duration(today_hours)}"
                )
                return

            attendance = await attendance_service.check_in(session, user, None, None)
            today_hours = await attendance_service.get_today_hours(session, user)
            remaining = config.DAILY_HOUR_LIMIT - today_hours
            ci = attendance.check_in_time

            await query.edit_message_text(
                f"✅ Kirish muvaffaqiyatli! Yaxshi smena! 🚀\n\n"
                f"💻 Joylashuv: Rocketchat\n"
                f"🕐 Kirish vaqti: {ci.hour:02d}:{ci.minute:02d}\n"
                f"📊 Bugun ishlangan: {_fmt_duration(today_hours)}\n"
                f"⏱️ Qolgan: {_fmt_duration(remaining)}"
            )

    elif choice == "loc_campus":
        # Ask for live location
        context.user_data['awaiting_live_location'] = True
        await query.edit_message_text(
            "📍 Iltimos, **jonli joylashuv** (Live Location) yuboring.\n\n"
            "Qo'shimcha (📎) → Joylashuv → \"Jonli joylashuvni ulashish\" ni tanlang.",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_action()
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Receive live location for Campus check-in"""
    location = update.message.location

    # Only accept live location (live_period is set)
    if not location.live_period:
        await update.message.reply_text(
            "❌ Faqat **jonli joylashuv** (Live Location) qabul qilinadi.\n\n"
            "Oddiy nuqta emas, \"Jonli joylashuvni ulashish\" ni tanlang.",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_action()
        )
        return

    if not context.user_data.get('awaiting_live_location'):
        return  # Not in checkin flow, ignore

    user_lat = location.latitude
    user_lng = location.longitude
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Foydalanuvchi topilmadi. /start buyrug'i orqali ro'yxatdan o'ting."
            )
            return

        # Guard: re-check active checkin & limit
        active = await attendance_service.get_active_checkin(session, user)
        if active:
            await update.message.reply_text(
                "⚠️ Siz allaqachon kirishni amalga oshirgansiz.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            context.user_data.pop('awaiting_live_location', None)
            return

        today_hours = await attendance_service.get_today_hours(session, user)
        if today_hours >= config.DAILY_HOUR_LIMIT:
            await update.message.reply_text(
                f"😴 Sizning kunlik limitingiz tugadi, dam oling!\n\n"
                f"Bugungi ishlangan vaqt: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            context.user_data.pop('awaiting_live_location', None)
            return

        # Validate distance
        is_valid, distance = location_service.is_within_work_location(user_lat, user_lng)

        if not is_valid:
            await update.message.reply_text(
                f"❌ Joylashuv tasdiqlanmadi!\n\n"
                f"Siz kampusdan {location_service.format_distance(distance)} masofadasiz.\n"
                f"Maksimal ruxsat: {config.MAX_DISTANCE_METERS} m\n\n"
                f"Iltimos, kampusga yaqinroq boring va qayta urinib ko'ring.",
                reply_markup=keyboards.cancel_action()
            )
            return  # Keep awaiting_live_location so they can retry

        # Check in
        attendance = await attendance_service.check_in(session, user, user_lat, user_lng)
        today_hours = await attendance_service.get_today_hours(session, user)
        remaining = config.DAILY_HOUR_LIMIT - today_hours
        ci = attendance.check_in_time

        await update.message.reply_text(
            f"✅ Kirish muvaffaqiyatli! Yaxshi smena! 🚀\n\n"
            f"🏫 Joylashuv: Kampus ({location_service.format_distance(distance)})\n"
            f"🕐 Kirish vaqti: {ci.hour:02d}:{ci.minute:02d}\n"
            f"📊 Bugun ishlangan: {_fmt_duration(today_hours)}\n"
            f"⏱️ Qolgan: {_fmt_duration(remaining)}",
            reply_markup=keyboards.main_menu(is_admin=user.is_admin)
        )

    context.user_data.pop('awaiting_live_location', None)
