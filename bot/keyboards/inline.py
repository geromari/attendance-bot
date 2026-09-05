from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ─── Reply keyboard button labels ───────────────────────────────────────────
BTN_CHECKIN     = "✅ Check-in"
BTN_CHECKOUT    = "🚪 Check-out"
BTN_PROFILE     = "👤 My Profile"
BTN_LEADERBOARD = "🏆 Leaderboard"
BTN_ANONYMOUS   = "📩 Anonymous Message"
BTN_ADMIN       = "🔧 Admin Panel"


class Keyboards:
    """Keyboard layouts for the bot"""

    # ── Main reply keyboard (bottom) ─────────────────────────────────────────
    @staticmethod
    def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Main menu as bottom reply keyboard"""
        keyboard = [
            [KeyboardButton(BTN_CHECKIN), KeyboardButton(BTN_CHECKOUT)],
            [KeyboardButton(BTN_PROFILE), KeyboardButton(BTN_LEADERBOARD)],
            [KeyboardButton(BTN_ANONYMOUS)],
        ]
        if is_admin:
            keyboard.append([KeyboardButton(BTN_ADMIN)])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def remove() -> ReplyKeyboardRemove:
        """Remove reply keyboard"""
        return ReplyKeyboardRemove()

    # ── Inline keyboards ──────────────────────────────────────────────────────
    @staticmethod
    def location_type() -> InlineKeyboardMarkup:
        """Choose check-in location type"""
        keyboard = [
            [
                InlineKeyboardButton("🏫 Campus", callback_data="loc_campus"),
                InlineKeyboardButton("💻 Rocketchat", callback_data="loc_rocketchat"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def cancel_action() -> InlineKeyboardMarkup:
        """Cancel action button"""
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def approval(telegram_id: int) -> InlineKeyboardMarkup:
        """Admin approval keyboard for new employee requests"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{telegram_id}"),
                InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{telegram_id}"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("➕ Add Schedule", callback_data="admin_add_schedule")],
            [InlineKeyboardButton("📋 All Schedules", callback_data="admin_view_schedules")],
            [InlineKeyboardButton("👥 All Employees", callback_data="admin_view_employees")],
            [InlineKeyboardButton("🗑 Remove Employee", callback_data="admin_remove_employee")],
            [InlineKeyboardButton("🚫 Rejected Requests", callback_data="admin_view_rejected")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def remove_employee_confirm(user_id: int) -> InlineKeyboardMarkup:
        """Confirmation keyboard before removing employee"""
        keyboard = [
            [InlineKeyboardButton("⚠️ Yes, Remove", callback_data=f"confirm_rm_{user_id}")],
            [InlineKeyboardButton("⬅️ Cancel", callback_data="admin_remove_employee")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def day_selection() -> InlineKeyboardMarkup:
        """Day selection keyboard for schedule"""
        days = [
            ("Monday", "day_0"), ("Tuesday", "day_1"),
            ("Wednesday", "day_2"), ("Thursday", "day_3"),
            ("Friday", "day_4"), ("Saturday", "day_5"),
            ("Sunday", "day_6"),
        ]
        keyboard = [
            [InlineKeyboardButton(day, callback_data=data) for day, data in days[i:i+2]]
            for i in range(0, len(days), 2)
        ]
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Back to admin menu button"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def unblock_user(telegram_id: int) -> InlineKeyboardMarkup:
        """Unblock / allow retry for a rejected employee"""
        keyboard = [
            [InlineKeyboardButton("🔄 Reset & Allow Retry", callback_data=f"unblock_{telegram_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_view_rejected")]
        ]
        return InlineKeyboardMarkup(keyboard)


keyboards = Keyboards()
