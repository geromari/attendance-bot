from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel inline callback — clears state, works inside & outside ConversationHandler"""
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text("❌ Action cancelled.")

    # Return END so ConversationHandler also exits when this is a fallback
    return ConversationHandler.END
