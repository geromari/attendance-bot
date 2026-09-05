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
            [InlineKeyboardButton("🗓 Haftalik ish jadvali", callback_data="admin_weekly_schedule")],
            [InlineKeyboardButton("📋 Barcha jadvallar", callback_data="admin_view_schedules")],
            [InlineKeyboardButton("👥 Barcha xodimlar", callback_data="admin_view_employees")],
            [InlineKeyboardButton("🗑 Xodimni o'chirish", callback_data="admin_remove_employee")],
            [InlineKeyboardButton("🚫 Rad etilgan so'rovlar", callback_data="admin_view_rejected")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def schedule_mode_menu(user_id: int) -> InlineKeyboardMarkup:
        """Weekly schedule mode selection menu"""
        keyboard = [
            [InlineKeyboardButton("⚡️ Dushanba - Juma (Mon-Fri)", callback_data=f"sched_preset_5_{user_id}")],
            [InlineKeyboardButton("⚡️ Dushanba - Shanba (Mon-Sat)", callback_data=f"sched_preset_6_{user_id}")],
            [InlineKeyboardButton("⚡️ Har kuni (7 kun / All days)", callback_data=f"sched_preset_7_{user_id}")],
            [InlineKeyboardButton("✍️ 7 kunni matn bilan kiritish", callback_data=f"sched_text_{user_id}")],
            [InlineKeyboardButton("📅 Kunma-kun to'g'irlash", callback_data=f"sched_days_{user_id}")],
            [InlineKeyboardButton("🗑 Barcha jadvallarni o'chirish", callback_data=f"sched_clear_{user_id}")],
            [InlineKeyboardButton("⬅️ Xodimlar ro'yxatiga", callback_data="admin_weekly_schedule")],
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def schedule_days_menu(user_id: int, schedules_dict: dict) -> InlineKeyboardMarkup:
        """Menu showing all 7 days with current times"""
        days = [
            ("Dush (Mon)", 0), ("Sesh (Tue)", 1),
            ("Chor (Wed)", 2), ("Pay (Thu)", 3),
            ("Jum (Fri)", 4), ("Shan (Sat)", 5),
            ("Yak (Sun)", 6),
        ]
        keyboard = []
        for name, day_num in days:
            if day_num in schedules_dict:
                s = schedules_dict[day_num]
                status = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
            else:
                status = "Dam olish"
            keyboard.append([
                InlineKeyboardButton(f"{name}: {status}", callback_data=f"sched_editday_{user_id}_{day_num}")
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"sched_user_{user_id}")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def schedule_day_action(user_id: int, day_num: int, has_schedule: bool) -> InlineKeyboardMarkup:
        """Action for a single day"""
        buttons = [
            [InlineKeyboardButton("⏱ Vaqtni kiritish", callback_data=f"sched_inputday_{user_id}_{day_num}")],
        ]
        if has_schedule:
            buttons.append([
                InlineKeyboardButton("🏖 Dam olish kuni qilish", callback_data=f"sched_dayoff_{user_id}_{day_num}")
            ])
        buttons.append([
            InlineKeyboardButton("⬅️ Orqaga", callback_data=f"sched_days_{user_id}")
        ])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def schedule_cancel_action(user_id: int) -> InlineKeyboardMarkup:
        """Cancel schedule edit button"""
        keyboard = [
            [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"sched_user_{user_id}")]
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
