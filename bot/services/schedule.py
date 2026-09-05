from datetime import time, datetime
from typing import List, Optional, Dict, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User, Schedule
from bot.utils.helpers import get_now

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
    async def set_bulk_days_schedule(
        session: AsyncSession,
        user: User,
        days: List[int],
        start_time: time,
        end_time: time,
        clear_others: bool = False
    ) -> List[Schedule]:
        """Set identical schedule for multiple days and optionally clear others"""
        updated = []
        for day in range(7):
            if day in days:
                sched = await ScheduleService.set_schedule(session, user, day, start_time, end_time)
                updated.append(sched)
            elif clear_others:
                await ScheduleService.delete_schedule(session, user, day)
        return updated

    @staticmethod
    async def set_weekly_schedule(
        session: AsyncSession,
        user: User,
        schedule_dict: Dict[int, Optional[Tuple[time, time]]]
    ):
        """Set full weekly schedule. If value is None, that day is a day off"""
        for day in range(7):
            if day in schedule_dict:
                times = schedule_dict[day]
                if times:
                    await ScheduleService.set_schedule(session, user, day, times[0], times[1])
                else:
                    await ScheduleService.delete_schedule(session, user, day)

    @staticmethod
    async def clear_all_user_schedules(session: AsyncSession, user: User) -> int:
        """Delete all schedules for a user"""
        result = await session.execute(
            select(Schedule).where(Schedule.user_id == user.id)
        )
        schedules = result.scalars().all()
        count = len(schedules)
        for s in schedules:
            await session.delete(s)
        await session.commit()
        return count

    @staticmethod
    async def get_user_schedule(session: AsyncSession, user: User) -> List[Schedule]:
        """Get all schedules for a user ordered by day_of_week"""
        result = await session.execute(
            select(Schedule).where(Schedule.user_id == user.id).order_by(Schedule.day_of_week)
        )
        return result.scalars().all()

    @staticmethod
    async def get_today_schedule(session: AsyncSession, user: User) -> Optional[Schedule]:
        """Get today's schedule for a user based on local timezone"""
        today_weekday = get_now().weekday()

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

