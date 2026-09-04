import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    WORK_LOCATION_LAT = float(os.getenv('WORK_LOCATION_LAT', '41.338938'))
    WORK_LOCATION_LNG = float(os.getenv('WORK_LOCATION_LNG', '69.337057'))
    MAX_DISTANCE_METERS = int(os.getenv('MAX_DISTANCE_METERS', '100'))
    DAILY_HOUR_LIMIT = int(os.getenv('DAILY_HOUR_LIMIT', '5'))
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./attendance.db')

config = Config()
