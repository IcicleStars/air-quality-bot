# Imports
# discord imports
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import MissingPermissions
from discord.app_commands.checks import has_permissions
# other imports
import os
from dotenv import load_dotenv
import requests
import datetime 
import json

# ====== CONFIGURATION ======
# Global variables
server_locations_cache = {}
LOCATIONS = "server_locations.json"

# initialize variables from env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENWEATHERMAP_API_KEY = os.getenv('API_KEY')
# Coordinates, default to Merced, California
DEFAULT_LAT = os.getenv('TEST_LATITUDE', "37.3022")
DEFAULT_LONG = os.getenv('TEST_LONGITUDE', "-120.4822")
DEFAULT_LOCATION_DISPLAY = "Merced, CA (Default location being used! Please set location with /setlocation command)"

# API Base URLs from env
# OpenWeatherMap Air Pollution Forecast
AIR_POLLUTION_FORECAST_API_URL = os.getenv('AIR_POLLUTION_FORECAST_API_URL')
# OpenWeatherMap Current Air Pollution
AIR_POLLUTION_CURRENT_API_URL = os.getenv('AIR_POLLUTION_CURRENT_API_URL')
# OpenWeatherMap Geocoding (Reverse)
REVERSE_GEOCODING_API_URL = os.getenv('REVERSE_GEOCODING_API_URL')
# OpenWeatherMap Geocoding (Direct)
GEOCODING_API_URL = os.getenv('DIRECT_GEOCODING_API_URL')


# define intents
intents = discord.Intents.default()

# bot instance
bot = commands.Bot(command_prefix='e!', intents=intents)

# ====== HELPER FUNCTIONS BELOW ======

# HELPER FUNCTION ( make API request )
async def make_api_request(url, params):
    """
    Makes an API request and returns the JSON response.
    Returns None if the request fails.
    Includes basic error handling and prints to console.
    """
    prepared_request = requests.Request('GET', url, params=params).prepare()

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        # Log details of the HTTP error
        print(f"HTTP error occurred: {http_err} - URL: {prepared_request.url} - Params: {params}")
    except requests.exceptions.ConnectionError as conn_err:
        # Log details of the connection error
        print(f"Connection error occurred: {conn_err} - URL: {prepared_request.url}")
    except requests.exceptions.Timeout as timeout_err:
        # Log details of the timeout error
        print(f"Timeout error occurred: {timeout_err} - URL: {prepared_request.url}")
    except requests.exceptions.RequestException as err:
        # Log details of any other request exception
        print(f"An error occurred during API request: {err} - URL: {prepared_request.url}")
    return None

# HELPER FUNCTION ( get AQI category )
def get_aqi_category(aqi_index):
    """Converts OpenWeatherMap AQI index (1-5) to a human-readable category."""
    categories = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }
    return categories.get(aqi_index, "Unknown") 

# HELPER FUNCTION ()
def load_server_locations(): 
    """Loads server locations"""
    global server_locations_cache
    try: 
        with open(LOCATIONS, 'r') as file:
            data = json.load(file)
            server_locations_cache = {int(k): v for k, v in data.items()} 
        print(f"Loaded server locations from {LOCATIONS}: {server_locations_cache}")
    except FileNotFoundError:
        print(f"File {LOCATIONS} not found. Using empty cache.")
        server_locations_cache = {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {LOCATIONS}. Using empty cache.")
        server_locations_cache = {}

def save_server_locations(): 
    """Saves current server locations."""
    with open(LOCATIONS, 'w') as file:
        json.dump(server_locations_cache, file, indent=4)
    print(f"Saved server locations to {LOCATIONS}: {server_locations_cache}")

# Helper function to get location data
def get_server_default_location(guild_id: int): 
    """
    Retrieves & returns lat, long, display name for guild
    """
    location_data = server_locations_cache.get(guild_id)
    if location_data:
        return location_data["lat"], location_data["lon"], location_data["display_name"]
    return None, None, None


# ====== EVENTS ======

# bot connected event
@bot.event
async def on_ready():
    """Called when the bot is successfully connected and ready."""
    print(f'{bot.user.name} has connected to Discord!')

    # Load server locations from file
    load_server_locations()

    # Check for OpenWeatherMap API Key (loaded from 'API_KEY' in .env)
    if OPENWEATHERMAP_API_KEY is None:
        print("WARNING: 'API_KEY' for OpenWeatherMap is not set in the .env file. The /aqi command will not work.")
    else:
        key_preview = OPENWEATHERMAP_API_KEY[:5] + "..." + OPENWEATHERMAP_API_KEY[-5:] if len(OPENWEATHERMAP_API_KEY) > 10 else OPENWEATHERMAP_API_KEY
        print(f"OpenWeatherMap API Key (from 'API_KEY' in .env) loaded: {key_preview}. Successfully loaded for /aqi.")

    # Sync global commands
    try:
        print("Attempting to sync global commands...")
        # Passing no arguments to sync() syncs all global commands.
        synced = await bot.tree.sync() 
        if synced:
            print(f"Synced {len(synced)} global application (slash) command(s):")
            for cmd in synced:
                print(f"  - {cmd.name}")
        else:
            print("No global commands were synced. This might happen if no commands are added to the tree or if there's an issue.")
    except Exception as e:
        print(f"Error syncing global application commands: {e}")


# ====== COMMANDS ======

# command for setting location for server
@bot.tree.command(name="setlocation", description="Sets default location for this server.")
@has_permissions(manage_guild=True)
async def set_location_slash(interaction: discord.Interaction, city: str, state_code: str = None, country_code: str = None): 
    """ 
    Sets the default location for this server.
    Provide city, state code if in US (e.g., CA for California), and country code (e.g., US for United States).
    State and country codes are optional.
    """
    if not interaction.guild_id: 
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True) 

    location_parts = [city]
    if state_code: 
        location_parts.append(state_code)
    if country_code:
        location_parts.append(country_code)

    query_location = ",".join(location_parts)

    geo_params = { 
        "q": query_location, 
        "limit": 1,
        "appid": OPENWEATHERMAP_API_KEY
    }

    # Make the API request to OpenWeatherMap Geocoding API
    geo_data_list = await make_api_request(GEOCODING_API_URL, geo_params)

    if not geo_data_list or not isinstance(geo_data_list, list) or len(geo_data_list) == 0:
        await interaction.followup.send(f"Could not find location '{query_location}'. Please check the spelling and try again.", ephemeral=True)
        return
    
    geo_data = geo_data_list[0]
    lat = geo_data.get("lat")
    lon = geo_data.get("lon")

    found_city = geo_data.get("name", city)
    found_state = geo_data.get("state", state_code)
    found_country = geo_data.get("country", country_code)

    display_name_parts = [found_city]
    if found_state: 
        display_name_parts.append(found_state)
    if found_country:
        display_name_parts.append(found_country)
    final_display_name = ", ".join(filter(None, display_name_parts))

    if lat is None or lon is None: 
        await interaction.followup.send(f"Found '{final_display_name}' but could not retrieve coordinates. Please check the location and try again.", ephemeral=True)
        return
    
    server_locations_cache[interaction.guild_id] = {
        "lat": lat,
        "lon": lon,
        "display_name": final_display_name,
        "set_by_user_id": interaction.user.id,
        "set_at": datetime.datetime.now().isoformat()
    }
    save_server_locations()

    await interaction.followup.send(f"Default location for this server has been set to: {final_display_name} (Lat: {lat}, Lon: {lon})", ephemeral=False)
# Set up permissions error
@set_location_slash.error
async def set_location_slash_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command. Please contact a server administrator.", ephemeral=True)
    else: 
        await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)
        print (f"Unexpected error in set_location_slash: {error}")

# command for EXPLAINING AQI
@bot.tree.command(name="aqi_info", description="Displays the meaning of AQI numbers.")
async def aqi_info_slash(interaction: discord.Interaction):
    """
    Displays the meaning of AQI numbers in a Discord embed message.
    This is a static command and does not require an API call.
    """
    # Create the embed message
    embed = discord.Embed(
        title="Air Quality Index (AQI) Categories",
        description="Understanding AQI values and their health implications.",
        color=discord.Color.blue()
    )
    
    # Add fields for each AQI category
    embed.add_field(name="1 - Good", value="Air quality is considered satisfactory, and air pollution poses little or no risk.", inline=False)
    embed.add_field(name="2 - Fair", value="Air quality is acceptable; however, there may be a risk for some people, particularly those who are unusually sensitive to air pollution.", inline=False)
    embed.add_field(name="3 - Moderate", value="Air quality is unhealthy for people unusually sensitive to air pollution.", inline=False)
    embed.add_field(name="4 - Poor", value="Air quality is unhealthy for sensitive groups. Members of sensitive groups may experience health effects. The general public is not likely to be affected.", inline=False)
    embed.add_field(name="5 - Very Poor", value="Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.", inline=False)
    embed.set_footer(text="Categories based on OpenWeatherMap AQI scale.")

    # Send the embed message
    await interaction.response.send_message(embed=embed, ephemeral=True)


# command for FETCHING AQI FORECAST
@bot.tree.command(name="aqi_f", description="Fetches air pollution forecast for the server's or global default location.")
async def aqi_slash_forecast(interaction: discord.Interaction):
    """
    Fetches and displays air pollution forecast.
    Uses server-specific location if set with /setlocation, otherwise uses global default.
    """

    # precautions
    if not OPENWEATHERMAP_API_KEY:
        await interaction.response.send_message(
            "Sorry, the API key for OpenWeatherMap air quality data is not configured. Please contact the bot administrator.",
            ephemeral=True
        )
        return

    # initialize location variables
    target_lat = DEFAULT_LAT
    target_lon = DEFAULT_LONG
    effective_location_display_for_embed = f"Merced (use /setlocation to set a location!)"
    full_location_description_for_user = DEFAULT_LOCATION_DISPLAY
    using_server_default = False

    # check if server-specific location is set
    if interaction.guild_id: 
        s_lat, s_lon, s_display_name = get_server_default_location(interaction.guild_id)
        if s_lat is not None and s_lon is not None:
            target_lat = s_lat
            target_lon = s_lon
            effective_location_display_for_embed = s_display_name if s_display_name else f"Lat: {s_lat:.2f}, Lon: {s_lon:.2f}"
            full_location_description_for_user = effective_location_display_for_embed
            using_server_default = True

    # global default
    initial_message = f"Fetching air pollution forecast for **{full_location_description_for_user}**..."
    await interaction.response.send_message(initial_message, ephemeral=False)

    # define api parameters
    aqi_params = {
        "lat": target_lat,
        "lon": target_lon,
        "appid": OPENWEATHERMAP_API_KEY
    }

    # make api request
    aqi_data = await make_api_request(AIR_POLLUTION_FORECAST_API_URL, aqi_params)

    # check if data is valid
    if aqi_data and "list" in aqi_data and aqi_data["list"]:
        selected_forecast_entry = None
        tomorrow_local_date = (datetime.datetime.now(datetime.timezone.utc).astimezone() + datetime.timedelta(days=1)).date()
        # find the aqi forecast entry for tomorrow
        for entry in aqi_data["list"]:
            dt_timestamp = entry.get("dt")
            if dt_timestamp:
                entry_local_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc).astimezone()
                if entry_local_datetime.date() == tomorrow_local_date:

                    if selected_forecast_entry is None or abs(entry_local_datetime.hour - 12) < abs(datetime.datetime.fromtimestamp(selected_forecast_entry.get("dt"), tz=datetime.timezone.utc).astimezone().hour - 12):
                        selected_forecast_entry = entry
        # if no entry found for tomorrow, find the next available entry
        if not selected_forecast_entry: 
            now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
            future_entries = [e for e in aqi_data["list"] if e.get("dt", 0) > now_ts]
            if future_entries:
                selected_forecast_entry = future_entries[0]
        # if still no entry found, return an error message
        if not selected_forecast_entry:
            await interaction.edit_original_response(content=f"Could not find a suitable air quality forecast for **{effective_location_display_for_embed}** in the API response.")
            return
        
        # get data
        aqi_index = selected_forecast_entry.get("main", {}).get("aqi", "N/A")
        components = selected_forecast_entry.get("components", {})
        dt_timestamp = selected_forecast_entry.get("dt")

        # format date
        forecast_date_str = "N/A"
        if dt_timestamp:
            utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
            local_datetime = utc_datetime.astimezone()
            forecast_date_str = local_datetime.strftime('%B %d, %Y at %I:%M %p %Z') 

        aqi_category = get_aqi_category(aqi_index)
        
        # set embed color based on aqi index
        embed_color = discord.Color.blue()
        if isinstance(aqi_index, int): 
            if aqi_index == 1: embed_color = discord.Color.green()
            elif aqi_index == 2: embed_color = discord.Color.yellow()
            elif aqi_index == 3: embed_color = discord.Color.orange()
            elif aqi_index == 4: embed_color = discord.Color.red()
            elif aqi_index == 5: embed_color = discord.Color.purple()

        # create embed
        embed = discord.Embed(
            title=f"Air Pollution Forecast for {effective_location_display_for_embed}",
            description=f"Forecast for: {forecast_date_str}",
            color=embed_color
        )
        embed.set_footer(text="Air quality data provided by OpenWeatherMap")
        embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)

        # add pollutant components
        components_text_parts = []
        pollutants_map = {
            "co": {"name": "CO (Carbon Monoxide)", "unit": "µg/m³"},
            "no": {"name": "NO (Nitrogen Monoxide)", "unit": "µg/m³"},
            "no2": {"name": "NO₂ (Nitrogen Dioxide)", "unit": "µg/m³"},
            "o3": {"name": "O₃ (Ozone)", "unit": "µg/m³"},
            "so2": {"name": "SO₂ (Sulphur Dioxide)", "unit": "µg/m³"},
            "pm2_5": {"name": "PM₂.₅ (Fine Particles)", "unit": "µg/m³"},
            "pm10": {"name": "PM₁₀ (Coarse Particles)", "unit": "µg/m³"},
            "nh3": {"name": "NH₃ (Ammonia)", "unit": "µg/m³"}
        }

        # iterate through pollutants and add to embed
        for key, details in pollutants_map.items():
            value = components.get(key)
            if value is not None:
                components_text_parts.append(f"**{details['name']}**: {value:.2f} {details['unit']}")
        
        if components_text_parts:
            embed.add_field(name="🧪 Pollutant Components", value="\n".join(components_text_parts), inline=False)
        else:
            embed.add_field(name="🧪 Pollutant Components", value="No specific component data available.", inline=False)

        await interaction.edit_original_response(content=None, embed=embed)

    # if no data found, return an error message
    else:
        error_message_content = f"Could not retrieve air quality forecast for **{effective_location_display_for_embed}**."
        if aqi_data and "message" in aqi_data:
            error_message_content += f" API Message: {aqi_data['message']}"
        else:
            error_message_content += " Please check bot logs for more details or try again later."
        await interaction.edit_original_response(content=error_message_content, embed=None)

# command for FETCHING CURRENT AQI
@bot.tree.command(name="aqi_c", description="Fetches current air pollution for the server's or global default location.")
async def aqi_slash_current(interaction: discord.Interaction):
    """
    Fetches and displays current air pollution.
    Uses server-specific location if set with /setlocation, otherwise uses global default.
    """

    # precautions
    if not OPENWEATHERMAP_API_KEY:
        await interaction.response.send_message(
            "Sorry, the API key for OpenWeatherMap air quality data is not configured. Please contact the bot administrator.",
            ephemeral=True
        )
        return

    # initialize location variables
    target_lat = DEFAULT_LAT
    target_lon = DEFAULT_LONG
    effective_location_display_for_embed = f"Merced (use /setlocation to set a location!)"
    full_location_description_for_user = DEFAULT_LOCATION_DISPLAY
    using_server_default = False

    # check if server-specific location is set
    if interaction.guild_id:
        s_lat, s_lon, s_display_name = get_server_default_location(interaction.guild_id)
        if s_lat is not None and s_lon is not None:
            target_lat = s_lat
            target_lon = s_lon
            effective_location_display_for_embed = s_display_name if s_display_name else f"Lat: {s_lat:.2f}, Lon: {s_lon:.2f}"
            full_location_description_for_user = effective_location_display_for_embed # For server-specific, this is the full info
            using_server_default = True
    # global default
    initial_message = f"Fetching current air pollution data for **{full_location_description_for_user}**..."
    await interaction.response.send_message(initial_message, ephemeral=False)

    # define api parameters
    aqi_params = {
        "lat": target_lat,
        "lon": target_lon,
        "appid": OPENWEATHERMAP_API_KEY
    }

    # make api request
    aqi_data = await make_api_request(AIR_POLLUTION_CURRENT_API_URL, aqi_params)

    # check if data is valid
    if aqi_data and "list" in aqi_data and aqi_data["list"]:
        current_entry = aqi_data["list"][0]
        aqi_index = current_entry.get("main", {}).get("aqi", "N/A")
        components = current_entry.get("components", {})
        dt_timestamp = current_entry.get("dt")

        # format date
        current_date_str = "N/A"
        if dt_timestamp:
            utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
            local_datetime = utc_datetime.astimezone()
            current_date_str = local_datetime.strftime('%B %d, %Y')

        aqi_category = get_aqi_category(aqi_index)
        
        # set embed color based on aqi index
        embed_color = discord.Color.blue()
        if isinstance(aqi_index, int): 
            if aqi_index == 1: embed_color = discord.Color.green()
            elif aqi_index == 2: embed_color = discord.Color.yellow()
            elif aqi_index == 3: embed_color = discord.Color.orange()
            elif aqi_index == 4: embed_color = discord.Color.red()
            elif aqi_index == 5: embed_color = discord.Color.purple()

        # create embed
        embed = discord.Embed(
            title=f"Current Air Pollution for {effective_location_display_for_embed}",
            description=f"Air Quality Index for Today ({current_date_str})",
            color=embed_color
        )
        embed.set_footer(text="Air quality data provided by OpenWeatherMap")
        embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)

        # add pollutant components
        components_text_parts = []
        pollutants_map = {
            "co": {"name": "CO (Carbon Monoxide)", "unit": "µg/m³"},
            "no": {"name": "NO (Nitrogen Monoxide)", "unit": "µg/m³"},
            "no2": {"name": "NO₂ (Nitrogen Dioxide)", "unit": "µg/m³"},
            "o3": {"name": "O₃ (Ozone)", "unit": "µg/m³"},
            "so2": {"name": "SO₂ (Sulphur Dioxide)", "unit": "µg/m³"},
            "pm2_5": {"name": "PM₂.₅ (Fine Particles)", "unit": "µg/m³"},
            "pm10": {"name": "PM₁₀ (Coarse Particles)", "unit": "µg/m³"},
            "nh3": {"name": "NH₃ (Ammonia)", "unit": "µg/m³"}
        }
        # iterate through pollutants and add to embed
        for key, details in pollutants_map.items():
            value = components.get(key)
            if value is not None:
                components_text_parts.append(f"**{details['name']}**: {value:.2f} {details['unit']}")
        
        if components_text_parts:
            embed.add_field(name="🧪 Pollutant Components", value="\n".join(components_text_parts), inline=False)
        else:
            embed.add_field(name="🧪 Pollutant Components", value="No specific component data available.", inline=False)

        await interaction.edit_original_response(content=None, embed=embed)
    else:
        error_message_content = f"Could not retrieve current air quality data for **{effective_location_display_for_embed}**."
        if aqi_data and "message" in aqi_data:
            error_message_content += f" API Message: {aqi_data['message']}"
        else:
            error_message_content += " Please check bot logs for more details or try again later."
        await interaction.edit_original_response(content=error_message_content, embed=None)


# ====== RUN BOT ======


if __name__ == "__main__":
    if TOKEN is None:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN is not set in the .env file. Bot cannot start.")
        exit()
    
    bot.run(TOKEN)
