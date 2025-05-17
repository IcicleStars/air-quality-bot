# Imports
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import requests
import datetime 

# initialize variables from env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID_STR = os.getenv('TEST_GUILD_ID')
OPENWEATHERMAP_API_KEY = os.getenv('API_KEY')
# Coordinates, default to Merced, California
TEST_LAT = os.getenv('TEST_LATITUDE', "37.3022")
TEST_LONG = os.getenv('TEST_LONGITUDE', "-120.4822")

# Convert GUILD_ID to int after loading
if GUILD_ID_STR:
    try:
        GUILD_ID = int(GUILD_ID_STR)
    except ValueError:
        print(f"CRITICAL ERROR: TEST_GUILD_ID '{GUILD_ID_STR}' is not a valid integer. Bot may not function correctly with guild-specific commands.")
        GUILD_ID = None 
else:
    print("CRITICAL ERROR: TEST_GUILD_ID is not set in .env file.")
    GUILD_ID = None 


# API Base URLs from env
# OpenWeatherMap Air Pollution Forecast
AIR_POLLUTION_FORECAST_API_URL = os.getenv('AIR_POLLUTION_FORECAST_API_URL')
# OpenWeatherMap Current Air Pollution
AIR_POLLUTION_CURRENT_API_URL = os.getenv('AIR_POLLUTION_CURRENT_API_URL')
# OpenWeatherMap Geocoding
GEOCODING_API_URL = os.getenv('GEOCODING_API_URL')


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
    # print(f"DEBUG: Attempting to request URL: {prepared_request.url}")

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

# ====== EVENTS ======

# bot connected event
@bot.event
async def on_ready():
    """Called when the bot is successfully connected and ready."""
    print(f'{bot.user.name} has connected to Discord!')
    if GUILD_ID: # Check if GUILD_ID was successfully converted
        guild = bot.get_guild(GUILD_ID) # Attempt to get the guild object
        if guild:
            print(f'Operating in guild: {guild.name} (ID: {GUILD_ID})')
        else:
            # This warning is important if guild-specific commands are not appearing
            print(f"Could not find guild with ID: {GUILD_ID}. Ensure the bot is in this server and the ID is correct.")
    else:
        print("WARNING: GUILD_ID is not properly configured. Guild-specific commands may not sync.")


    # Check for OpenWeatherMap API Key (loaded from 'API_KEY' in .env)
    if OPENWEATHERMAP_API_KEY is None:
        print("WARNING: 'API_KEY' for OpenWeatherMap is not set in the .env file. The /aqi command will not work.")
    else:
        key_preview = OPENWEATHERMAP_API_KEY[:5] + "..." + OPENWEATHERMAP_API_KEY[-5:] if len(OPENWEATHERMAP_API_KEY) > 10 else OPENWEATHERMAP_API_KEY
        print(f"OpenWeatherMap API Key (from 'API_KEY' in .env) loaded: {key_preview}. Successfully loaded for /aqi.")


    if GUILD_ID:
        try:
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"Synced {len(synced)} application (slash) command(s) to guild {GUILD_ID}.")
        except Exception as e:
            print(f"Error syncing application commands: {e}")
    else:
        print("Skipping command sync due to invalid GUILD_ID.")


# ====== COMMANDS ======

# command for displaying what the aqi numbers mean
@bot.tree.command(name="aqi_info", description="Displays the meaning of AQI numbers.", guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
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

# command for fetching air pollution forecast
@bot.tree.command(name="aqi_f", description="Fetches air pollution forecast (OpenWeatherMap).", guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
async def aqi_slash_forecase(interaction: discord.Interaction):
    """
    Fetches and displays air pollution forecast using OpenWeatherMap API
    for the pre-configured latitude and longitude.
    """

    # Precautions
    if not OPENWEATHERMAP_API_KEY:
        await interaction.response.send_message("Sorry, the API key for OpenWeatherMap air quality data is not configured. Please contact the bot administrator.", ephemeral=True)
        return
    if not GUILD_ID:
        await interaction.response.send_message("Bot's guild ID is not configured correctly. Please contact an admin.", ephemeral=True)
        return

    # acknowledge user while loading
    await interaction.response.send_message("Fetching air pollution forecast from OpenWeatherMap...", ephemeral=False) 

    # Define the parameters for the API requests
    aqi_params = {
        "lat": TEST_LAT,
        "lon": TEST_LONG,
        "appid": OPENWEATHERMAP_API_KEY 
    }

    city_params = { 
        "lat": TEST_LAT,
        "lon": TEST_LONG,
        "limit": 1, 
        "appid": OPENWEATHERMAP_API_KEY
    }

    # Make the API requests
    aqi_data = await make_api_request(AIR_POLLUTION_FORECAST_API_URL, aqi_params)
    day_data = await make_api_request(GEOCODING_API_URL, city_params)

    location_display_name = f"{TEST_LAT}, {TEST_LONG}"

    # Check if day_data is valid 
    if day_data and isinstance(day_data, list) and len(day_data) > 0: 
        # Get the city name from the first entry in the list
        city_name = day_data[0].get("name", None)
        # Get country name
        country_name = day_data[0].get("country", None)
        # If in US, get the state name
        state_name = day_data[0].get("state", None)

        # more readable date
        if city_name:
            location_parts = [city_name]
            if state_name and country_name == "US": 
                location_parts.append(state_name)
            if country_name:
                location_parts.append(country_name)
            location_display_name = ", ".join(location_parts)


    # check if aqi_data is valid
    if aqi_data and "list" in aqi_data and aqi_data["list"]:
        # Find the forecast for tomorrow
        selected_forecast_entry = None
        tomorrow_local_date = (datetime.datetime.now().astimezone() + datetime.timedelta(days=1)).date()
        # print(f"DEBUG: Looking for forecast for tomorrow's date: {tomorrow_local_date.strftime('%B %d, %Y')}")


        for entry in aqi_data["list"]:
            dt_timestamp = entry.get("dt")
            if dt_timestamp:
                # Convert entry's UTC timestamp to local datetime object
                entry_local_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc).astimezone()
                if entry_local_datetime.date() == tomorrow_local_date:
                    selected_forecast_entry = entry
                    print(f"DEBUG: Found forecast entry for tomorrow: {entry_local_datetime.strftime('%B %d, %Y %H:%M:%S')}")
                    break

        if not selected_forecast_entry:
            await interaction.edit_original_response(content=f"Could not find an air quality forecast for tomorrow ({tomorrow_local_date.strftime('%B %d, %Y')}) in the API response.")
            return

        # Continue using selected_forecast_entry
        aqi_index = selected_forecast_entry.get("main", {}).get("aqi", "N/A")
        components = selected_forecast_entry.get("components", {}) 
        dt_timestamp = selected_forecast_entry.get("dt")  

        # Convert UNIX timestamp to a readable date/time stringdate_str = "N/A"
        if dt_timestamp:
            # Create a datetime object from the UTC timestamp
            utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
            # Convert to server's local time
            local_datetime = utc_datetime.astimezone() 
            # Format to "{month} {day}, {year}"
            forecast_date_str = local_datetime.strftime('%B %d, %Y')


            aqi_category = get_aqi_category(aqi_index) 
            
            # color based on AQI index (for fun)
            embed_color = discord.Color.blue()
            if aqi_index == 1: embed_color = discord.Color.green()
            elif aqi_index == 2: embed_color = discord.Color.yellow()
            elif aqi_index == 3: embed_color = discord.Color.orange()
            elif aqi_index == 4: embed_color = discord.Color.red()
            elif aqi_index == 5: embed_color = discord.Color.purple()

            # create embed message
            embed = discord.Embed(
                title=f"Air Pollution Forecast for {location_display_name}",
                description=f"Forecast Date: {forecast_date_str}", 
                color=embed_color
            )
            embed.set_footer(text="Air quality data provided by OpenWeatherMap")

            # add AQI field to the embed
            embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)
            
            components_text_parts = []
            # define known pollutants for display names and units
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

            # iterate through the pollutant map and add data if present in the API response
            for key, details in pollutants_map.items():
                value = components.get(key) 
                if value is not None:
                    components_text_parts.append(f"**{details['name']}**: {value:.2f} {details['unit']}")
            
            # add pollutant components field to the embed
            if components_text_parts:
                embed.add_field(name="🧪 Pollutant Components", value="\n".join(components_text_parts), inline=False)
            else:
                embed.add_field(name="🧪 Pollutant Components", value="No specific component data available.", inline=False)

            # EDIT the original fetching message with the new embed content
            await interaction.edit_original_response(content=None, embed=embed)
        else: 
            await interaction.edit_original_response(content="Could not determine forecast timestamp from API data.")
            return 
    else:
        # cases where API data is not as expected or an error occurred
        error_message = "Could not retrieve air quality data from OpenWeatherMap."
        if aqi_data and "message" in aqi_data: 
            error_message += f" API Message: {aqi_data['message']}"
        else:
            # error if no specific message from API
            error_message += " Please check bot logs for more details or try again later."
        await interaction.edit_original_response(content=error_message)

# command for fetching current air pollution
@bot.tree.command(name="aqi_c", description="Fetches current air pollution (OpenWeatherMap).", guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
async def aqi_slash_current(interaction: discord.Interaction):
    """
    Fetches and displays current air pollution using OpenWeatherMap API
    for the pre-configured latitude and longitude.
    """

    # Precautions
    if not OPENWEATHERMAP_API_KEY:
        await interaction.response.send_message("Sorry, the API key for OpenWeatherMap air quality data is not configured. Please contact the bot administrator.", ephemeral=True)
        return
    if not GUILD_ID:
        await interaction.response.send_message("Bot's guild ID is not configured correctly. Please contact an admin.", ephemeral=True)
        return

    # acknowledge user while loading
    await interaction.response.send_message("Fetching air pollution current from OpenWeatherMap...", ephemeral=False) 

    # Define the parameters for the API requests
    aqi_params = {
        "lat": TEST_LAT,
        "lon": TEST_LONG,
        "appid": OPENWEATHERMAP_API_KEY 
    }

    city_params = { 
        "lat": TEST_LAT,
        "lon": TEST_LONG,
        "limit": 1, 
        "appid": OPENWEATHERMAP_API_KEY
    }

    # Make the API requests
    aqi_data = await make_api_request(AIR_POLLUTION_CURRENT_API_URL, aqi_params)
    day_data = await make_api_request(GEOCODING_API_URL, city_params)

    location_display_name = f"{TEST_LAT}, {TEST_LONG}"

    # Check if day_data is valid 
    if day_data and isinstance(day_data, list) and len(day_data) > 0: 
        # Get the city name from the first entry in the list
        city_name = day_data[0].get("name", None)
        # Get country name
        country_name = day_data[0].get("country", None)
        # If in US, get the state name
        state_name = day_data[0].get("state", None)

        # Construct a more friendly location string
        if city_name:
            location_parts = [city_name]
            if state_name and country_name == "US": 
                location_parts.append(state_name)
            if country_name:
                location_parts.append(country_name)
            location_display_name = ", ".join(location_parts)


    # check if aqi_data is valid
    if aqi_data and "list" in aqi_data and aqi_data["list"]:
        # Get the first current AQI data point from the list
        current_entry = aqi_data["list"][0]
        aqi_index = current_entry.get("main", {}).get("aqi", "N/A")
        components = current_entry.get("components", {}) 
        dt_timestamp = current_entry.get("dt")         

        # convert timestamp to readable date and time
        current_date_str = "N/A"
        if dt_timestamp:
            # Create a datetime object from the UTC timestamp
            utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
            # Convert to server's local time
            local_datetime = utc_datetime.astimezone()
            # Format to "{month} {day}, {year}"
            current_date_str = local_datetime.strftime('%B %d, %Y')


            aqi_category = get_aqi_category(aqi_index) 
            
            # color based on AQI index (for fun)
            embed_color = discord.Color.blue()
            if aqi_index == 1: embed_color = discord.Color.green()
            elif aqi_index == 2: embed_color = discord.Color.yellow()
            elif aqi_index == 3: embed_color = discord.Color.orange()
            elif aqi_index == 4: embed_color = discord.Color.red()
            elif aqi_index == 5: embed_color = discord.Color.purple()

            # create embed message
            embed = discord.Embed(
                title=f"Current Air Pollution for {location_display_name}",
                description=f"Air Quality Index for Today ({current_date_str})", 
                color=embed_color
            )
            embed.set_footer(text="Air quality data provided by OpenWeatherMap")

            # add AQI field to the embed
            embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)
            
            components_text_parts = []
            # define known pollutants for display names and units
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

            # iterate through the pollutant map and add data if present in the API response
            for key, details in pollutants_map.items():
                value = components.get(key) 
                if value is not None:
                    components_text_parts.append(f"**{details['name']}**: {value:.2f} {details['unit']}")
            
            # add pollutant components field to the embed
            if components_text_parts:
                embed.add_field(name="🧪 Pollutant Components", value="\n".join(components_text_parts), inline=False)
            else:
                embed.add_field(name="🧪 Pollutant Components", value="No specific component data available.", inline=False)

            # EDIT the original fetching message with the new embed content
            await interaction.edit_original_response(content=None, embed=embed)
        else: 
            await interaction.edit_original_response(content="Could not determine current timestamp from API data.")
            return 
    else:
        # cases where API data is not as expected or an error occurred
        error_message = "Could not retrieve air quality data from OpenWeatherMap."
        if aqi_data and "message" in aqi_data: 
            error_message += f" API Message: {aqi_data['message']}"
        else:
            # error if no specific message from API
            error_message += " Please check bot logs for more details or try again later."
        await interaction.edit_original_response(content=error_message)



# ====== RUN BOT ======


if __name__ == "__main__":
    if TOKEN is None:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN is not set in the .env file. Bot cannot start.")
        exit()
    if GUILD_ID is None: 
        print("CRITICAL ERROR: TEST_GUILD_ID is not set correctly in .env or is invalid. Bot may not function as expected.")
        bot.run(TOKEN)
    
    bot.run(TOKEN)
