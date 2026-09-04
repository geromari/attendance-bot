from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.attendance import attendance_service
from bot.keyboards.inline import keyboards
from database.db import async_session


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel inline callback — clears state, works inside & outside ConversationHandler"""
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text("❌ Amal bekor qilindi.")

    # Return END so ConversationHandler also exits when this is a fallback
    return ConversationHandler.END
