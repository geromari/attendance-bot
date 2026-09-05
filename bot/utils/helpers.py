"""Utility helper functions"""

from datetime import datetime, timedelta, time
from typing import Optional, Tuple
import re
import pytz
from bot.config import config


def get_now() -> datetime:
    """Get current datetime in configured timezone (default Asia/Tashkent) without tzinfo"""
    tz_name = getattr(config, 'TIMEZONE', 'Asia/Tashkent')
    try:
        tz = pytz.timezone(tz_name)
        return datetime.now(tz).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def parse_time_range(text: str) -> Optional[Tuple[time, time]]:
    """Parse time range like '09:00 - 18:00', '9:00-18:00', '09:00 18:00'"""
    # Remove leading numbering like '1.', '1)', '1 -', 'Dushanba:'
    cleaned = re.sub(r'^\s*(?:[1-7]|[a-zA-Zа-яА-Я]+)[\.\)\:\-]\s*', '', text.strip())
    # Match HH:MM ... HH:MM
    matches = re.findall(r'(\d{1,2}):(\d{2})', cleaned)
    if len(matches) >= 2:
        try:
            h1, m1 = int(matches[0][0]), int(matches[0][1])
            h2, m2 = int(matches[1][0]), int(matches[1][1])
            if 0 <= h1 < 24 and 0 <= m1 < 60 and 0 <= h2 < 24 and 0 <= m2 < 60:
                return time(h1, m1), time(h2, m2)
        except (ValueError, IndexError):
            pass

    # Fallback to single numbers: e.g. 9 - 18 or 9 18
    matches2 = re.findall(r'\b(\d{1,2})\b', cleaned)
    if len(matches2) >= 2:
        try:
            h1, h2 = int(matches2[0]), int(matches2[1])
            if 0 <= h1 < 24 and 0 <= h2 < 24:
                return time(h1, 0), time(h2, 0)
        except (ValueError, IndexError):
            pass

    return None


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
