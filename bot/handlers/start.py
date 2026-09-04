from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from config import config

WAITING_NICKNAME = 1

WELCOME_TEXT = (
    "👋 *Davomat botiga xush kelibsiz!*\n\n"
    "Bu bot orqali siz:\n"
    "✅ *Kirish* — ish boshlanishini belgilash\n"
    "🚪 *Chiqish* — ish tugashini belgilash\n"
    "👤 *Mening profilim* — haftalik statistika\n"
    "🏆 *Reyting* — eng faol xodimlar\n\n"
    "📍 *Kirish qoidalari:*\n"
    "• *Kampus* — jonli joylashuv (Live Location) talab qilinadi\n"
    "• *Rocketchat* — joylashuv talab qilinmaydi\n\n"
    "⏱️ Kunlik limit: *{limit} soat*\n\n"
    "——————————————\n"
    "Ro'yxatdan o'tish uchun o'z *taxallusingizni* kiriting:"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)

        if user:
            await update.message.reply_text(
                f"Xush kelibsiz, {user.nickname}! 👋\n\nAmalni tanlang:",
                reply_markup=keyboards.main_menu(is_admin=user.is_admin)
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
        # Nickname already taken?
        existing = await attendance_service.get_user_by_nickname(session, nickname)
        if existing:
            await update.message.reply_text(
                "❌ Bu taxallus allaqachon band.\n"
                "Iltimos, boshqa taxallus kiriting:"
            )
            return WAITING_NICKNAME

        # Already registered with this telegram_id?
        existing_by_id = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        if existing_by_id:
            await update.message.reply_text(
                f"Siz allaqachon ro'yxatdansiz: *{existing_by_id.nickname}*",
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
        await update.message.reply_text(
            f"✅ Ro'yxatdan o'tish muvaffaqiyatli!\n\nIsm: *{user.nickname}* 👑",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=True)
        )
        return ConversationHandler.END

    # Store pending registration in bot_data
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
                    f"🔔 *Yangi xodim so'rovi*\n\n"
                    f"👤 Ism: {full_name}\n"
                    f"📛 Taxallus: *{nickname}*\n"
                    f"🆔 Telegram ID: `{telegram_id}`\n\n"
                    f"Tasdiqlaysizmi?"
                ),
                parse_mode='Markdown',
                reply_markup=keyboards.approval(telegram_id)
            )
        except Exception:
            pass  # Admin might have blocked bot

    await update.message.reply_text(
        f"⏳ So'rovingiz adminga yuborildi.\n\n"
        f"Taxallusingiz *{nickname}* tasdiqlanishini kuting..."
        , parse_mode='Markdown'
    )
    return ConversationHandler.END


async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approved a new employee"""
    query = update.callback_query
    await query.answer()

    admin_id = update.effective_user.id
    if admin_id not in config.ADMIN_IDS:
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    target_telegram_id = int(query.data.split('_')[1])
    pending = context.application.bot_data.get('pending', {})
    info = pending.get(target_telegram_id)

    if not info:
        await query.edit_message_text("⚠️ Bu so'rov allaqachon ko'rib chiqilgan.")
        return

    nickname = info['nickname']
    full_name = info['full_name']

    async with async_session() as session:
        # Double-check nickname not taken
        existing = await attendance_service.get_user_by_nickname(session, nickname)
        if existing:
            pending.pop(target_telegram_id, None)
            await query.edit_message_text(
                f"⚠️ *{nickname}* taxallusi allaqachon band bo'lib qoldi."
                , parse_mode='Markdown'
            )
            try:
                await context.bot.send_message(
                    chat_id=target_telegram_id,
                    text="❌ Kechirasiz, sizning taxallusingiz allaqachon band bo'lib qoldi.\n"
                         "Qaytadan ro'yxatdan o'tish uchun /start bosing."
                )
            except Exception:
                pass
            return

        user = await attendance_service.get_or_create_user(
            session, target_telegram_id, nickname, full_name
        )

    pending.pop(target_telegram_id, None)

    await query.edit_message_text(
        f"✅ *{nickname}* tasdiqlandi va tizimga qo'shildi.", parse_mode='Markdown'
    )

    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=(
                f"✅ *Tabriklaymiz!* Taxallusingiz *{nickname}* tasdiqlandi.\n\n"
                f"Amalni tanlang:"
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
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    target_telegram_id = int(query.data.split('_')[1])
    pending = context.application.bot_data.get('pending', {})
    info = pending.pop(target_telegram_id, None)

    if not info:
        await query.edit_message_text("⚠️ Bu so'rov allaqachon ko'rib chiqilgan.")
        return

    nickname = info['nickname']

    await query.edit_message_text(
        f"❌ *{nickname}* rad etildi.", parse_mode='Markdown'
    )

    try:
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=(
                f"❌ Kechirasiz, *{nickname}* taxallusiga ro'yxatdan o'tish rad etildi.\n\n"
                f"Boshqa taxallus bilan urinib ko'rish uchun /start bosing."
            ),
            parse_mode='Markdown'
        )
    except Exception:
        pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Amal bekor qilindi.")
    return ConversationHandler.END
