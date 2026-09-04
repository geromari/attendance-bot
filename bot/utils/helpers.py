"""Utility helper functions"""

from datetime import datetime, timedelta
from typing import Optional


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_week_bounds(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Get start and end of week for given date"""
    if date is None:
        date = datetime.now()

    start_of_week = date - timedelta(days=date.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    end_of_week = start_of_week + timedelta(days=7)

    return start_of_week, end_of_week


def is_weekend(date: Optional[datetime] = None) -> bool:
    """Check if given date is weekend"""
    if date is None:
        date = datetime.now()
    return date.weekday() >= 5


def get_day_name(day_of_week: int) -> str:
    """Get day name from day of week (0=Monday, 6=Sunday)"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if 0 <= day_of_week < 7:
        return days[day_of_week]
    return 'Unknown'
