from datetime import datetime, timedelta, time
from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User, Attendance, Schedule, RegistrationRequest
from bot.config import config

class AttendanceService:
    """Service for managing attendance records"""

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_id: int,
        nickname: str,
        full_name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                nickname=nickname,
                full_name=full_name,
                is_admin=telegram_id in config.ADMIN_IDS
            )
            session.add(user)
            await session.commit()

        return user

    @staticmethod
    async def get_user_by_nickname(session: AsyncSession, nickname: str) -> Optional[User]:
        """Get user by nickname"""
        result = await session.execute(
            select(User).where(User.nickname == nickname)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_registration_request(session: AsyncSession, telegram_id: int) -> Optional[RegistrationRequest]:
        """Get registration request by telegram ID"""
        result = await session.execute(
            select(RegistrationRequest).where(RegistrationRequest.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_or_update_registration_request(
        session: AsyncSession,
        telegram_id: int,
        nickname: str,
        full_name: Optional[str] = None,
        status: str = 'pending'
    ) -> RegistrationRequest:
        """Create or update registration request"""
        req = await AttendanceService.get_registration_request(session, telegram_id)
        if req:
            req.nickname = nickname
            req.full_name = full_name
            req.status = status
        else:
            req = RegistrationRequest(
                telegram_id=telegram_id,
                nickname=nickname,
                full_name=full_name,
                status=status
            )
            session.add(req)
        await session.commit()
        return req

    @staticmethod
    async def update_registration_status(
        session: AsyncSession,
        telegram_id: int,
        status: str
    ) -> Optional[RegistrationRequest]:
        """Update registration request status"""
        req = await AttendanceService.get_registration_request(session, telegram_id)
        if req:
            req.status = status
            await session.commit()
        return req

    @staticmethod
    async def get_all_rejected_requests(session: AsyncSession) -> List[RegistrationRequest]:
        """Get all rejected registration requests"""
        result = await session.execute(
            select(RegistrationRequest).where(RegistrationRequest.status == 'rejected')
        )
        return result.scalars().all()

    @staticmethod
    async def delete_registration_request(session: AsyncSession, telegram_id: int) -> bool:
        """Delete registration request (e.g. to allow retry)"""
        req = await AttendanceService.get_registration_request(session, telegram_id)
        if req:
            await session.delete(req)
            await session.commit()
            return True
        return False

    @staticmethod
    async def check_in(
        session: AsyncSession,
        user: User,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> Attendance:
        """Create a new check-in record"""
        attendance = Attendance(
            user_id=user.id,
            check_in_time=datetime.now(),
            check_in_location_lat=lat,
            check_in_location_lng=lng
        )
        session.add(attendance)
        await session.commit()
        return attendance


    @staticmethod
    async def check_out(
        session: AsyncSession,
        user: User,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        is_auto: bool = False,
        notes: Optional[str] = None
    ) -> Optional[Attendance]:
        """Check out from active session"""
        # Find active check-in
        result = await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.check_out_time.is_(None)
                )
            )
        )
        attendance = result.scalar_one_or_none()

        if attendance:
            attendance.check_out_time = datetime.now()
            attendance.check_out_location_lat = lat
            attendance.check_out_location_lng = lng
            attendance.is_auto_checkout = is_auto
            attendance.notes = notes
            await session.commit()

        return attendance

    @staticmethod
    async def get_active_checkin(session: AsyncSession, user: User) -> Optional[Attendance]:
        """Get active check-in if exists"""
        result = await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.check_out_time.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_today_hours(session: AsyncSession, user: User) -> float:
        """Get total hours worked today"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        result = await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.check_in_time >= today,
                    Attendance.check_in_time < tomorrow
                )
            )
        )
        records = result.scalars().all()

        total_hours = 0.0
        for record in records:
            total_hours += record.duration_hours

        return total_hours

    @staticmethod
    async def get_week_hours(session: AsyncSession, user: User) -> float:
        """Get total hours worked this week"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)

        result = await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.check_in_time >= start_of_week,
                    Attendance.check_in_time < end_of_week
                )
            )
        )
        records = result.scalars().all()

        total_hours = 0.0
        for record in records:
            total_hours += record.duration_hours

        return total_hours

    @staticmethod
    async def get_week_days_worked(session: AsyncSession, user: User) -> List[str]:
        """Get list of days worked this week"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)

        result = await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.check_in_time >= start_of_week,
                    Attendance.check_in_time < end_of_week
                )
            )
        )
        records = result.scalars().all()

        days = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for record in records:
            day_name = day_names[record.check_in_time.weekday()]
            if day_name not in days:
                days.append(day_name)

        return days

    @staticmethod
    async def get_all_users_with_week_hours(session: AsyncSession) -> List[tuple]:
        """Get all users with their weekly hours for leaderboard"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)

        # Query users with their attendance records
        result = await session.execute(
            select(User)
        )
        users = result.scalars().all()

        leaderboard = []
        for user in users:
            hours = await AttendanceService.get_week_hours(session, user)
            leaderboard.append((user, hours))

        # Sort by hours descending
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        return leaderboard


attendance_service = AttendanceService()
