"""
Weather Service – uses Open-Meteo (free, no API key needed).
Returns current conditions + 7-day forecast for a lat/lon.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail",
}


def get_weather(latitude: float, longitude: float) -> dict:
    """Fetch current weather and 7-day forecast."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "precipitation", "weathercode",
        ],
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "weathercode",
        ],
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return _parse(data)
    except Exception as exc:
        logger.error("Weather fetch error: %s", exc)
        return _mock_weather()


def _parse(data: dict) -> dict:
    cur = data.get("current", {})
    daily = data.get("daily", {})

    current = {
        "temperature": cur.get("temperature_2m"),
        "humidity": cur.get("relative_humidity_2m"),
        "wind_speed": cur.get("wind_speed_10m"),
        "precipitation": cur.get("precipitation"),
        "condition": WMO_CODES.get(cur.get("weathercode", 0), "Unknown"),
        "time": cur.get("time", ""),
    }

    forecast = []
    times = daily.get("time", [])
    for i, day in enumerate(times):
        forecast.append({
            "date": day,
            "max_temp": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
            "min_temp": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
            "precipitation": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
            "condition": WMO_CODES.get(
                daily.get("weathercode", [])[i] if i < len(daily.get("weathercode", [])) else 0,
                "Unknown"
            ),
        })

    return {"current": current, "forecast": forecast}


def weather_to_text(weather: dict) -> str:
    """Convert weather dict to a short text summary for the AI prompt."""
    c = weather.get("current", {})
    lines = [
        f"Temperature: {c.get('temperature')}°C",
        f"Humidity: {c.get('humidity')}%",
        f"Wind Speed: {c.get('wind_speed')} km/h",
        f"Precipitation: {c.get('precipitation')} mm",
        f"Condition: {c.get('condition')}",
    ]
    fc = weather.get("forecast", [])[:3]
    if fc:
        lines.append("3-Day Forecast:")
        for day in fc:
            lines.append(
                f"  {day['date']}: {day['condition']}, "
                f"{day['min_temp']}–{day['max_temp']}°C, "
                f"Rain: {day['precipitation']} mm"
            )
    return "\n".join(lines)


def _mock_weather() -> dict:
    """Return sample data when API is unreachable."""
    return {
        "current": {
            "temperature": 28, "humidity": 65,
            "wind_speed": 12, "precipitation": 0,
            "condition": "Partly cloudy", "time": "N/A",
        },
        "forecast": [
            {"date": "Day 1", "max_temp": 32, "min_temp": 22, "precipitation": 2, "condition": "Partly cloudy"},
            {"date": "Day 2", "max_temp": 30, "min_temp": 21, "precipitation": 5, "condition": "Light rain"},
            {"date": "Day 3", "max_temp": 29, "min_temp": 20, "precipitation": 8, "condition": "Moderate rain"},
        ],
    }
