from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Time, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    nickname = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, nickname='{self.nickname}')>"


class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="schedules")

    def __repr__(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f"<Schedule(user_id={self.user_id}, day='{days[self.day_of_week]}', time='{self.start_time}-{self.end_time}')>"


class Attendance(Base):
    __tablename__ = 'attendance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime, nullable=True)
    check_in_location_lat = Column(Float, nullable=True)
    check_in_location_lng = Column(Float, nullable=True)
    check_out_location_lat = Column(Float, nullable=True)
    check_out_location_lng = Column(Float, nullable=True)
    is_auto_checkout = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="attendance_records")

    def __repr__(self):
        return f"<Attendance(user_id={self.user_id}, check_in='{self.check_in_time}', check_out='{self.check_out_time}')>"

    @property
    def duration_hours(self):
        """Calculate duration in hours"""
        if self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return delta.total_seconds() / 3600
        return 0


class RegistrationRequest(Base):
    __tablename__ = 'registration_requests'

    telegram_id = Column(BigInteger, primary_key=True)
    nickname = Column(String(50), nullable=False)
    full_name = Column(String(100))
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RegistrationRequest(telegram_id={self.telegram_id}, nickname='{self.nickname}', status='{self.status}')>"

