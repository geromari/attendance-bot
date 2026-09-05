import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from bot.config import config

logger = logging.getLogger(__name__)

WAITING_ANON_MESSAGE = 1


async def start_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle click on Anonymous Message button"""
    telegram_id = update.effective_user.id

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ Please register first by sending /start."
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "💬 **Send Anonymous Message to Admin**\n\n"
        "Please type your message below. Your identity (name, username, ID) will remain completely anonymous and confidential.\n\n"
        "Send /cancel to cancel.",
        parse_mode='Markdown',
        reply_markup=keyboards.cancel_action()
    )
    return WAITING_ANON_MESSAGE


async def receive_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user's anonymous message to all admins without identifying information"""
    telegram_id = update.effective_user.id
    text = update.message.text or update.message.caption or ""
    has_photo = bool(update.message.photo)

    if not text and not has_photo:
        await update.message.reply_text(
            "Please send a text message or a photo with a description.\n"
            "Send /cancel to cancel."
        )
        return WAITING_ANON_MESSAGE

    # Deliver to all admins anonymously
    delivered = 0
    for admin_id in config.ADMIN_IDS:
        try:
            if has_photo:
                photo_file_id = update.message.photo[-1].file_id
                caption = (
                    "📩 **New Anonymous Message**\n"
                    "━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{text}\n\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "*(Sender identity is completely hidden)*"
                )
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=caption,
                    parse_mode='Markdown'
                )
            else:
                msg_content = (
                    "📩 **New Anonymous Message**\n"
                    "━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{text}\n\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "*(Sender identity is completely hidden)*"
                )
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=msg_content,
                    parse_mode='Markdown'
                )
            delivered += 1
        except Exception as e:
            logger.error(f"Failed to deliver anonymous message to admin {admin_id}: {e}")

    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        is_admin = user.is_admin if user else False

    if delivered > 0:
        await update.message.reply_text(
            "✅ **Your anonymous message has been sent to the administrator.**\n\n"
            "Your identity remains completely confidential.",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(is_admin=is_admin)
        )
    else:
        await update.message.reply_text(
            "⚠️ Administrator is currently unreachable. Please try again later.",
            reply_markup=keyboards.main_menu(is_admin=is_admin)
        )

    return ConversationHandler.END


async def cancel_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel anonymous message sending"""
    telegram_id = update.effective_user.id
    async with async_session() as session:
        user = await attendance_service.get_user_by_telegram_id(session, telegram_id)
        is_admin = user.is_admin if user else False

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Cancelled. Your message was not sent.")
    else:
        await update.message.reply_text(
            "❌ Cancelled. Your message was not sent.",
            reply_markup=keyboards.main_menu(is_admin=is_admin)
        )

    return ConversationHandler.END
