from geopy.distance import geodesic
from config import config

class LocationService:
    """Service for location-based validation"""

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in meters"""
        point1 = (lat1, lng1)
        point2 = (lat2, lng2)
        return geodesic(point1, point2).meters

    @staticmethod
    def is_within_work_location(user_lat: float, user_lng: float) -> tuple[bool, float]:
        """
        Check if user is within allowed work location
        Returns: (is_valid, distance_in_meters)
        """
        distance = LocationService.calculate_distance(
            user_lat, user_lng,
            config.WORK_LOCATION_LAT, config.WORK_LOCATION_LNG
        )
        is_valid = distance <= config.MAX_DISTANCE_METERS
        return is_valid, distance

    @staticmethod
    def format_distance(distance_meters: float) -> str:
        """Format distance for display"""
        if distance_meters < 1000:
            return f"{int(distance_meters)}m"
        else:
            return f"{distance_meters/1000:.2f}km"


location_service = LocationService()
