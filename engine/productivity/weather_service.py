"""
WeatherService: Real-time weather and forecast via OpenWeatherMap free tier.
Auto-detects the user's city via IP geolocation.
"""
import json
import os
import requests

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config.json"
)
BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherService:

    @classmethod
    def _get_api_key(cls) -> str:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)["openweather_api_key"]

    @classmethod
    def _resolve_city(cls, city: str | None) -> str:
        if city and city.lower() != "auto":
            return city
        try:
            res = requests.get("http://ip-api.com/json/", timeout=5).json()
            return res.get("city", "London")
        except Exception:
            return "London"

    @classmethod
    def get_current(cls, city: str | None = None) -> str:
        try:
            key = cls._get_api_key()
            city = cls._resolve_city(city)
            url = f"{BASE_URL}/weather?q={city}&appid={key}&units=metric"
            data = requests.get(url, timeout=10).json()

            if data.get("cod") != 200:
                return f"Could not retrieve weather for {city}."

            temp   = data["main"]["temp"]
            feels  = data["main"]["feels_like"]
            desc   = data["weather"][0]["description"].capitalize()
            hum    = data["main"]["humidity"]
            wind   = data["wind"]["speed"]

            return (
                f"{city} right now: {desc}. "
                f"Temperature {temp:.1f}°C, feels like {feels:.1f}°C. "
                f"Humidity {hum}%, wind {wind} m/s."
            )
        except Exception as e:
            return f"Weather check failed: {e}"

    @classmethod
    def get_forecast(cls, city: str | None = None) -> str:
        try:
            key = cls._get_api_key()
            city = cls._resolve_city(city)
            # cnt=8 → 8 three-hour slots ≈ 24 hours
            url = f"{BASE_URL}/forecast?q={city}&appid={key}&units=metric&cnt=8"
            data = requests.get(url, timeout=10).json()

            if str(data.get("cod")) != "200":
                return f"Could not retrieve forecast for {city}."

            items = data["list"]
            # Show every 4th slot (every 12 hours)
            summaries = []
            for item in items[::4]:
                dt   = item["dt_txt"]
                desc = item["weather"][0]["description"].capitalize()
                temp = item["main"]["temp"]
                summaries.append(f"{dt}: {desc}, {temp:.1f}°C")

            return f"Forecast for {city}: " + " | ".join(summaries)
        except Exception as e:
            return f"Forecast failed: {e}"

    @classmethod
    def will_it_rain(cls, city: str | None = None) -> str:
        try:
            key = cls._get_api_key()
            city = cls._resolve_city(city)
            url = f"{BASE_URL}/forecast?q={city}&appid={key}&units=metric&cnt=4"
            data = requests.get(url, timeout=10).json()

            descriptions = [
                item["weather"][0]["description"]
                for item in data.get("list", [])
            ]
            if any("rain" in d or "drizzle" in d for d in descriptions):
                return "Yes boss, rain is expected in the next few hours. Carry an umbrella."
            return "No rain expected in the next few hours. Skies should be clear."
        except Exception as e:
            return f"Rain check failed: {e}"
