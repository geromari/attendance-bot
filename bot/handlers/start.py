from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from bot.config import config

WAITING_NICKNAME = 1

WELCOME_TEXT = (
    "👋 *Welcome to the Attendance Bot!*\n\n"
    "With this bot you can:\n"
    "✅ *Check-in* — mark start of your shift\n"
    "🚪 *Check-out* — mark end of your shift\n"
    "👤 *My Profile* — weekly statistics\n"
    "🏆 *Leaderboard* — top active employees\n"
    "📩 *Anonymous Message* — send confidential feedback to admin\n\n"
    "📍 *Check-in rules:*\n"
    "• *Campus* — Live Location required\n"
    "• *Rocketchat* — No location required\n\n"
    "⏱️ Daily limit: *{limit} hours*\n\n"
    "——————————————\n"
    "Please enter your assigned *nickname* to register:"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if user:
            await update.message.reply_text(
                f"Welcome back, {user.nickname}! 👋\n\nChoose an action:",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
            )
            return ConversationHandler.END

        # Check if user has a pending or rejected registration request
        reg_req = await attendance_service.get_registration_request(session, telegram_id)
        if reg_req:
            if reg_req.status == 'rejected':
                await update.message.reply_text(
                    "❌ **Access Denied**\n\nYou do not work here.",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
            elif reg_req.status == 'pending':
                await update.message.reply_text(
                    f"⏳ Your registration request for nickname *{reg_req.nickname}* is pending admin approval.\n\n"
                    f"Please wait for confirmation from the administrator.",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END

    # New user — show welcome + instructions
    await update.message.reply_text(
        WELCOME_TEXT.format(limit=config.DAILY_HOUR_LIMIT),
        parse_mode='Markdown'
    )
    return WAITING_NICKNAME


async def receive_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle nickname input — send approval request to admins"""
    telegram_id = update.effective_user.id
    nickname = update.message.text.strip()
    full_name = update.effective_user.full_name or nickname

    async with async_session() as session:
        # Check if user was rejected
        reg_req = await attendance_service.get_registration_request(session, telegram_id)
        if reg_req and reg_req.status == 'rejected':
            await update.message.reply_text(
                "❌ **Access Denied**\n\nYou do not work here.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Nickname already taken?
        existing = await attendance_service.get_user_by_nickname(session, nickname)
        if existing:
            await update.message.reply_text(
                "❌ This nickname is already taken.\n"
                "Please enter a different nickname:"
            )
            return WAITING_NICKNAME

        # Already registered with this telegram_id?
        existing_by_id = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        if existing_by_id:
            await update.message.reply_text(
                f"You are already registered as: *{existing_by_id.nickname}*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu(is_admin=existing_by_id.is_admin)
            )
            return ConversationHandler.END

    # If sender IS an admin — register immediately without approval
    if telegram_id in config.ADMIN_IDS:
        async with async_session() as session:
            user = await attendance_service.get_or_create_user(
                session, telegram_id, nickname, full_name
            )
            await attendance_service.create_or_update_registration_request(
                session, telegram_id, nickname, full_name, status='approved'
            )
        await update.message.reply_text(
            f"✅ Registration successful!\n\nName: *{user.nickname}* 👑",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=True)
        )
        return ConversationHandler.END

    # Save pending request in DB and bot_data
    async with async_session() as session:
        await attendance_service.create_or_update_registration_request(
            session, telegram_id, nickname, full_name, status='pending'
        )

    if 'pending' not in context.application.bot_data:
        context.application.bot_data['pending'] = {}

    context.application.bot_data['pending'][telegram_id] = {
        'nickname': nickname,
        'full_name': full_name,
    }

    # Notify all admins
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 *New Employee Registration Request*\n\n"
                    f"👤 Name: {full_name}\n"
                    f"📛 Nickname: *{nickname}*\n"
                    f"🆔 Telegram ID: `{telegram_id}`\n\n"
                    f"Do you approve this employee?"
                ),
                parse_mode='Markdown',
                reply_markup=keyboards.approval(telegram_id)
            )
        except Exception:
            pass  # Admin might have blocked bot

    await update.message.reply_text(
        f"⏳ Your request has been sent to the administrator.\n\n"
        f"Please wait for your nickname *{nickname}* to be approved..."
        , parse_mode='Markdown'
    )
    return ConversationHandler.END


async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approved a new employee"""
    query = update.callback_query
    await query.answer()

    admin_id = update.effective_user.id
    if admin_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    target_telegram_id = int(query.data.split('_')[1])
    
    async with async_session() as session:
        reg_req = await attendance_service.get_registration_request(session, target_telegram_id)
        pending = context.application.bot_data.get('pending', {})
        info = pending.get(target_telegram_id)

        nickname = (reg_req.nickname if reg_req else None) or (info.get('nickname') if info else None)
        full_name = (reg_req.full_name if reg_req else None) or (info.get('full_name') if info else None)

        if not nickname:
            await query.edit_message_text("⚠️ This request has already been processed.")
            return

        # Double-check nickname not taken
        existing = await attendance_service.get_user_by_nickname(session, nickname)
        if existing and existing.telegram_id != target_telegram_id:
            pending.pop(target_telegram_id, None)
            await attendance_service.update_registration_status(session, target_telegram_id, 'rejected')
            await query.edit_message_text(
                f"⚠️ *{nickname}* nickname is already taken."
                , parse_mode='Markdown'
            )
            try:
                await context.bot.send_message(
                    chat_id=target_telegram_id,
                    text="❌ Sorry, your nickname has already been taken by another employee.\n"
                         "Please send /start to try registering with a different nickname."
                )
            except Exception:
                pass
            return

        user = await attendance_service.get_or_create_user(
            session, target_telegram_id, nickname, full_name
        )
        await attendance_service.update_registration_status(session, target_telegram_id, 'approved')

    if 'pending' in context.application.bot_data:
        context.application.bot_data['pending'].pop(target_telegram_id, None)

    await query.edit_message_text(
        f"✅ *{nickname}* has been approved and added to the system.", parse_mode='Markdown'
    )

    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=(
                f"✅ *Congratulations!* Your nickname *{nickname}* has been approved.\n\n"
                f"Choose an action:"
            ),
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=False)
        )
    except Exception:
        pass


async def handle_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejected a new employee"""
    query = update.callback_query
    await query.answer()

    admin_id = update.effective_user.id
    if admin_id not in config.ADMIN_IDS:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    target_telegram_id = int(query.data.split('_')[1])

    async with async_session() as session:
        reg_req = await attendance_service.get_registration_request(session, target_telegram_id)
        pending = context.application.bot_data.get('pending', {})
        info = pending.pop(target_telegram_id, None)

        nickname = (reg_req.nickname if reg_req else None) or (info.get('nickname') if info else "Employee")
        await attendance_service.create_or_update_registration_request(
            session, target_telegram_id, nickname, status='rejected'
        )

    await query.edit_message_text(
        f"❌ *{nickname}* has been rejected.", parse_mode='Markdown'
    )

    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text="❌ **Access Denied**\n\nYou do not work here.",
            parse_mode='Markdown'
        )
    except Exception:
        pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Action cancelled.")
    return ConversationHandler.END
