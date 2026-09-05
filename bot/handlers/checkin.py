from telegram import Update
from telegram.ext import ContextTypes
from bot.services.attendance import attendance_service
from bot.services.location import location_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from bot.config import config


def _fmt_duration(hours: float) -> str:
    """Format duration as 'Xh Ym'"""
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f"{h}h {m}m"
    elif h:
        return f"{h}h"
    else:
        return f"{m}m"


# ─── Reply keyboard button handler ───────────────────────────────────────────

async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: User pressed Check-in — ask which location type"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Please register first by sending /start."
            )
            return

        # Already checked in?
        active_checkin = await attendance_service.get_active_checkin(session, user)
        if active_checkin:
            await update.message.reply_text(
                "⚠️ You are already checked in.\nPlease check out first.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return

        # Daily limit reached?
        today_hours = await attendance_service.get_today_hours(session, user)
        if today_hours >= config.DAILY_HOUR_LIMIT:
            await update.message.reply_text(
                f"😴 You have reached your daily limit. Time to rest!\n\n"
                f"Hours worked today: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return

    # Ask location type
    await update.message.reply_text(
        "🏢 Where are you working from?",
        reply_markup=keyboards.location_type()
    )


async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checkout directly without location"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if not user:
            await update.message.reply_text(
                "❌ Please register first by sending /start."
            )
            return

        active_checkin = await attendance_service.get_active_checkin(session, user)
        if not active_checkin:
            await update.message.reply_text(
                "⚠️ No active check-in found.\nPlease check in first.",
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
                f"✅ Checked out successfully! Have a great day! 🌟\n\n"
                f"🕐 Check-in: {ci.hour:02d}:{ci.minute:02d}\n"
                f"🕐 Check-out: {co.hour:02d}:{co.minute:02d}\n"
                f"⏱️ Session: {_fmt_duration(duration)}\n"
                f"📊 Today total: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
        else:
            await update.message.reply_text(
                "❌ No active check-in found.",
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
                    f"😴 You have reached your daily limit. Time to rest!\n\n"
                    f"Hours worked today: {_fmt_duration(today_hours)}"
                )
                return

            attendance = await attendance_service.check_in(session, user, None, None)
            today_hours = await attendance_service.get_today_hours(session, user)
            remaining = max(0.0, config.DAILY_HOUR_LIMIT - today_hours)
            ci = attendance.check_in_time

            await query.edit_message_text(
                f"✅ Check-in successful! Have a productive shift! 🚀\n\n"
                f"💻 Location: Rocketchat\n"
                f"🕐 Check-in time: {ci.hour:02d}:{ci.minute:02d}\n"
                f"📊 Worked today: {_fmt_duration(today_hours)}\n"
                f"⏱️ Remaining: {_fmt_duration(remaining)}"
            )

    elif choice == "loc_campus":
        # Ask for live location
        context.user_data['awaiting_live_location'] = True
        await query.edit_message_text(
            "📍 Please send your **Live Location**.\n\n"
            "Tap Attach (📎) → Location → \"Share Live Location\".",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_action()
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Receive live location for Campus check-in"""
    location = update.message.location

    # Only accept live location (live_period is set)
    if not location.live_period:
        await update.message.reply_text(
            "❌ Only **Live Location** is accepted.\n\n"
            "Please select \"Share Live Location\", not a static pin.",
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
                "❌ User not found. Please register using /start."
            )
            return

        # Guard: re-check active checkin & limit
        active = await attendance_service.get_active_checkin(session, user)
        if active:
            await update.message.reply_text(
                "⚠️ You are already checked in.",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            context.user_data.pop('awaiting_live_location', None)
            return

        today_hours = await attendance_service.get_today_hours(session, user)
        if today_hours >= config.DAILY_HOUR_LIMIT:
            await update.message.reply_text(
                f"😴 You have reached your daily limit. Time to rest!\n\n"
                f"Hours worked today: {_fmt_duration(today_hours)}",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            context.user_data.pop('awaiting_live_location', None)
            return

        # Validate distance
        is_valid, distance = location_service.is_within_work_location(user_lat, user_lng)

        if not is_valid:
            await update.message.reply_text(
                f"❌ Location not verified!\n\n"
                f"You are {location_service.format_distance(distance)} away from campus.\n"
                f"Maximum allowed distance: {config.MAX_DISTANCE_METERS} m\n\n"
                f"Please get closer to campus and try again.",
                reply_markup=keyboards.cancel_action()
            )
            return  # Keep awaiting_live_location so they can retry

        # Check in
        attendance = await attendance_service.check_in(session, user, user_lat, user_lng)
        today_hours = await attendance_service.get_today_hours(session, user)
        remaining = max(0.0, config.DAILY_HOUR_LIMIT - today_hours)
        ci = attendance.check_in_time

        await update.message.reply_text(
            f"✅ Check-in successful! Have a productive shift! 🚀\n\n"
            f"🏫 Location: Campus ({location_service.format_distance(distance)})\n"
            f"🕐 Check-in time: {ci.hour:02d}:{ci.minute:02d}\n"
            f"📊 Worked today: {_fmt_duration(today_hours)}\n"
            f"⏱️ Remaining: {_fmt_duration(remaining)}",
            reply_markup=keyboards.main_menu(is_admin=user.is_admin)
        )

    context.user_data.pop('awaiting_live_location', None)
