"""
ON3RT Radio Suite
libraries/weather

Service météo partagé de la suite (WeatherService) et son contrat de
données (voir weather_service.py).
"""

from .weather_service import WeatherService

__all__ = ["WeatherService"]
