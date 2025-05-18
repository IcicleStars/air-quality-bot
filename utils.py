# HOLDS HELPER FUNCTIONS
# Imports
import requests
import json
import datetime
import config

# MAKES API REQUESTS
async def make_api_request(url, params):
    """
    Makes an API request and returns the JSON response.
    Returns None if the request fails.
    Includes basic error handling and prints to console.
    """
    prepared_request = requests.Request('GET', url, params=params).prepare()
    session = requests.Session() # Use a session for potentially better performance

    try:
        response = session.send(prepared_request, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - URL: {prepared_request.url} - Params: {params}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err} - URL: {prepared_request.url}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err} - URL: {prepared_request.url}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred during API request: {err} - URL: {prepared_request.url}")
    finally:
        session.close()
    return None

# GETS AQI CATEGORY
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

# GETS WEATHER DATA
def load_server_locations_from_file(file_path: str):
    """Loads server locations from the specified file."""
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            # Ensure keys are integers if they represent guild_ids
            return {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        print(f"Location file {file_path} not found. Starting with an empty cache.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}. Starting with an empty cache.")
        return {}

# SAVES SERVER LOCATIONS
def save_server_locations_to_file(server_locations_data: dict, file_path: str):
    """Saves current server locations to the specified file."""
    try:
        with open(file_path, 'w') as file:
            json.dump(server_locations_data, file, indent=4)
        print(f"Saved server locations to {file_path}")
    except IOError as e:
        print(f"Error saving server locations to {file_path}: {e}")

# GETS SERVER DEFAULT LOCATION
def get_server_default_location(guild_id: int, server_locations_data: dict):
    """
    Retrieves & returns lat, long, display name for a guild from the provided cache.
    """
    location_data = server_locations_data.get(guild_id)
    if location_data:
        return location_data["lat"], location_data["lon"], location_data["display_name"]
    return None, None, None

# GETS COORDINATES FROM API
async def get_coordinates_from_api(city: str, state_code: str, country_code: str, api_key: str, geo_url: str):
    """Helper to fetch coordinates for a given location string from OpenWeatherMap."""
    location_parts = [city]
    if state_code:
        location_parts.append(state_code)
    if country_code:
        location_parts.append(country_code)
    query_location = ",".join(location_parts)

    geo_params = {
        "q": query_location,
        "limit": 1,
        "appid": api_key
    }
    geo_data_list = await make_api_request(geo_url, geo_params)

    if not geo_data_list or not isinstance(geo_data_list, list) or len(geo_data_list) == 0:
        return None, None, f"Could not find location '{query_location}'."

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
        return None, None, f"Found '{final_display_name}' but could not retrieve coordinates."

    return lat, lon, final_display_name