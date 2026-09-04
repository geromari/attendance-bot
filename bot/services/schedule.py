from datetime import time, datetime
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User, Schedule

class ScheduleService:
    """Service for managing work schedules"""

    @staticmethod
    async def set_schedule(
        session: AsyncSession,
        user: User,
        day_of_week: int,
        start_time: time,
        end_time: time
    ) -> Schedule:
        """Set or update schedule for a specific day"""
        # Check if schedule exists for this day
        result = await session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.day_of_week == day_of_week
                )
            )
        )
        schedule = result.scalar_one_or_none()

        if schedule:
            schedule.start_time = start_time
            schedule.end_time = end_time
        else:
            schedule = Schedule(
                user_id=user.id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            session.add(schedule)

        await session.commit()
        return schedule

    @staticmethod
    async def get_user_schedule(session: AsyncSession, user: User) -> List[Schedule]:
        """Get all schedules for a user"""
        result = await session.execute(
            select(Schedule).where(Schedule.user_id == user.id)
        )
        return result.scalars().all()

    @staticmethod
    async def get_today_schedule(session: AsyncSession, user: User) -> Optional[Schedule]:
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

    @staticmethod
    async def delete_schedule(
        session: AsyncSession,
        user: User,
        day_of_week: int
    ) -> bool:
        """Delete schedule for a specific day"""
        result = await session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.day_of_week == day_of_week
                )
            )
        )
        schedule = result.scalar_one_or_none()

        if schedule:
            await session.delete(schedule)
            await session.commit()
            return True
        return False


schedule_service = ScheduleService()
