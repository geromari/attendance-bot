from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ─── Reply keyboard button labels ───────────────────────────────────────────
BTN_CHECKIN    = "✅ Kirish"
BTN_CHECKOUT   = "🚪 Chiqish"
BTN_PROFILE    = "👤 Mening profilim"
BTN_LEADERBOARD = "🏆 Reyting"
BTN_ADMIN      = "🔧 Admin panel"


class Keyboards:
    """Keyboard layouts for the bot"""

    # ── Main reply keyboard (bottom) ─────────────────────────────────────────
    @staticmethod
    def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Main menu as bottom reply keyboard"""
        keyboard = [
            [KeyboardButton(BTN_CHECKIN), KeyboardButton(BTN_CHECKOUT)],
            [KeyboardButton(BTN_PROFILE), KeyboardButton(BTN_LEADERBOARD)],
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
                InlineKeyboardButton("🏫 Kampus", callback_data="loc_campus"),
                InlineKeyboardButton("💻 Rocketchat", callback_data="loc_rocketchat"),
            ],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def cancel_action() -> InlineKeyboardMarkup:
        """Cancel action button"""
        keyboard = [
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def approval(telegram_id: int) -> InlineKeyboardMarkup:
        """Admin approval keyboard for new employee requests"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{telegram_id}"),
                InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{telegram_id}"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("➕ Jadval qo'shish", callback_data="admin_add_schedule")],
            [InlineKeyboardButton("📋 Barcha jadvallar", callback_data="admin_view_schedules")],
            [InlineKeyboardButton("👥 Barcha xodimlar", callback_data="admin_view_employees")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def day_selection() -> InlineKeyboardMarkup:
        """Day selection keyboard for schedule"""
        days = [
            ("Dushanba", "day_0"), ("Seshanba", "day_1"),
            ("Chorshanba", "day_2"), ("Payshanba", "day_3"),
            ("Juma", "day_4"), ("Shanba", "day_5"),
            ("Yakshanba", "day_6"),
        ]
        keyboard = [
            [InlineKeyboardButton(day, callback_data=data) for day, data in days[i:i+2]]
            for i in range(0, len(days), 2)
        ]
        keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)


keyboards = Keyboards()
