# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENWEATHERMAP_API_KEY = os.getenv('API_KEY')

# Coordinates, default to Merced, California
DEFAULT_LAT = os.getenv('TEST_LATITUDE', "37.3022")
DEFAULT_LONG = os.getenv('TEST_LONGITUDE', "-120.4822")
DEFAULT_LOCATION_DISPLAY = "Merced, CA (Default location being used! Please set location with /setlocation command)"
TEST_GUILD_ID = os.getenv('TEST_GUILD_ID', None)
if TEST_GUILD_ID: 
    TEST_GUILD_ID = int(TEST_GUILD_ID)


# API Base URLs
AIR_POLLUTION_FORECAST_API_URL = os.getenv('AIR_POLLUTION_FORECAST_API_URL', "http://api.openweathermap.org/data/2.5/air_pollution/forecast")
AIR_POLLUTION_CURRENT_API_URL = os.getenv('AIR_POLLUTION_CURRENT_API_URL', "http://api.openweathermap.org/data/2.5/air_pollution")
REVERSE_GEOCODING_API_URL = os.getenv('REVERSE_GEOCODING_API_URL', "http://api.openweathermap.org/geo/1.0/reverse")
GEOCODING_API_URL = os.getenv('DIRECT_GEOCODING_API_URL', "http://api.openweathermap.org/geo/1.0/direct")
CURRENT_WEATHER_API_URL = os.getenv('WEATHER_API_URL', "http://api.openweathermap.org/data/2.5/weather")
WEATHER_FORECAST_API_URL = os.getenv('WEATHER_FORECAST_API_URL', "http://api.openweathermap.org/data/2.5/forecast") 

# File for storing server locations
LOCATIONS_FILE = "server_locations.json"