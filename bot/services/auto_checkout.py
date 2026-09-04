import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from database.db import async_session
from bot.models.user import User, Attendance, Schedule
from bot.services.attendance import attendance_service
from ..config import config
import logging

logger = logging.getLogger(__name__)

class AutoCheckoutService:
    """Service for automatic checkout based on time limits and schedules"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def check_and_auto_checkout(self):
        """Check all active check-ins and auto checkout if needed"""
        logger.info("Running auto-checkout check...")

        async with async_session() as session:
            # Get all active check-ins
            result = await session.execute(
                select(Attendance).where(Attendance.check_out_time.is_(None))
            )
            active_checkins = result.scalars().all()

            for attendance in active_checkins:
                user_result = await session.execute(
                    select(User).where(User.id == attendance.user_id)
                )
                user = user_result.scalar_one_or_none()

                if not user:
                    continue

                should_checkout = False
                reason = ""

                # Check 1: Daily hour limit
                today_hours = await attendance_service.get_today_hours(session, user)
                if today_hours >= config.DAILY_HOUR_LIMIT:
                    should_checkout = True
                    reason = f"Daily limit reached ({config.DAILY_HOUR_LIMIT}h)"

                # Check 2: Schedule end time
                if not should_checkout:
                    today_schedule = await self._get_today_schedule(session, user)
                    if today_schedule:
                        now = datetime.now().time()
                        if now >= today_schedule.end_time:
                            should_checkout = True
                            reason = f"Work schedule ended ({today_schedule.end_time.strftime('%H:%M')})"

                # Perform auto checkout
                if should_checkout:
                    await attendance_service.check_out(
                        session, user,
                        lat=attendance.check_in_location_lat,
                        lng=attendance.check_in_location_lng,
                        is_auto=True,
                        notes=f"Auto checkout: {reason}"
                    )
                    logger.info(f"Auto checkout performed for {user.nickname}: {reason}")

                    # Try to notify user
                    try:
                        from telegram import Bot
                        bot = Bot(token=config.BOT_TOKEN)
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"🤖 **Auto Checkout**\n\n"
                                 f"You have been automatically checked out.\n"
                                 f"Reason: {reason}\n\n"
                                 f"Check-in: {attendance.check_in_time.strftime('%H:%M')}\n"
                                 f"Check-out: {datetime.now().strftime('%H:%M')}\n"
                                 f"Duration: {(datetime.now() - attendance.check_in_time).total_seconds() / 3600:.2f}h",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {user.nickname}: {e}")

    async def _get_today_schedule(self, session, user: User):
        """Get today's schedule for a user"""
        today_weekday = datetime.now().weekday()

        result = await session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.day_of_week == today_weekday
                )
            )
        )
        return result.scalar_one_or_none()

    def start(self):
        """Start the auto checkout scheduler"""
        # Check every 5 minutes
        self.scheduler.add_job(
            self.check_and_auto_checkout,
            trigger=IntervalTrigger(minutes=5),
            id='auto_checkout_check',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Auto checkout scheduler started")

    def stop(self):
        """Stop the auto checkout scheduler"""
        self.scheduler.shutdown()
        logger.info("Auto checkout scheduler stopped")


auto_checkout_service = AutoCheckoutService()
