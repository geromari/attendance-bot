from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from bot.services.attendance import attendance_service
from bot.services.schedule import schedule_service
from bot.keyboards.inline import keyboards
from database.db import async_session
from bot.config import config
from datetime import time
from bot.models.user import User

# Admin conversation states
WAITING_NICKNAME_FOR_SCHEDULE = 1
WAITING_DAY = 2
WAITING_START_TIME = 3
WAITING_END_TIME = 4

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAY_NAMES_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


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


async def handle_add_schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add schedule conversation"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if telegram_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            "❌ Access denied. For admins only.",
            reply_markup=keyboards.back_to_main()
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ **Add Schedule**\n\n"
        "Enter employee's nickname:",
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
                f"❌ Employee with nickname '{nickname}' not found.\n\n"
                f"Please enter a valid nickname:",
                reply_markup=keyboards.cancel_action()
            )
            return WAITING_NICKNAME_FOR_SCHEDULE

        context.user_data['schedule_user_id'] = user.id
        context.user_data['schedule_user_nickname'] = nickname

        await update.message.reply_text(
            f"✅ Employee: {nickname}\n\n"
            f"Select day of week:",
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
        f"✅ Day: {DAY_NAMES[day_of_week]}\n\n"
        f"Enter start time in HH:MM format (e.g. 09:00):",
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
            f"✅ Start time: {start_time.strftime('%H:%M')}\n\n"
            f"Enter end time in HH:MM format (e.g. 17:00):",
            reply_markup=keyboards.cancel_action()
        )

        return WAITING_END_TIME

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Invalid time format. Please enter in HH:MM format (e.g. 09:00):",
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
            user = await session.get(User, user_id)
            if user:
                await schedule_service.set_schedule(
                    session, user, day_of_week, start_time, end_time
                )

                await update.message.reply_text(
                    f"✅ Schedule saved successfully!\n\n"
                    f"Employee: {nickname}\n"
                    f"Day: {DAY_NAMES[day_of_week]}\n"
                    f"Hours: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                    reply_markup=keyboards.admin_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ Error: User not found.",
                    reply_markup=keyboards.admin_menu()
                )

        context.user_data.clear()
        return ConversationHandler.END

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Invalid time format. Please enter in HH:MM format (e.g. 17:00):",
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

