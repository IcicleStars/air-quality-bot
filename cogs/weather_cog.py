# Imports
import discord
from discord import app_commands
from discord.ext import commands
import datetime

import utils
import config

class WeatherCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # helper function to get location
    async def _get_effective_location(self, interaction: discord.Interaction, city: str = None, state_code: str = None, country_code: str = None):
        """Helper to determine target lat/lon and display names."""
        if city:
            lat, lon, display_name_or_error = await utils.get_coordinates_from_api(
                city, state_code, country_code,
                self.bot.config.OPENWEATHERMAP_API_KEY,
                self.bot.config.GEOCODING_API_URL
            )
            if lat is None or lon is None:
                return None, None, None, display_name_or_error
            
            full_location_desc = f"{display_name_or_error} (Lat: {lat:.2f}, Lon: {lon:.2f})"
            return lat, lon, display_name_or_error, full_location_desc
        else:
            target_lat = self.bot.config.DEFAULT_LAT
            target_lon = self.bot.config.DEFAULT_LONG
            effective_display = self.bot.config.DEFAULT_LOCATION_DISPLAY.split('(')[0].strip()
            full_location_desc = self.bot.config.DEFAULT_LOCATION_DISPLAY

            if interaction.guild_id:
                s_lat, s_lon, s_display_name = utils.get_server_default_location(
                    interaction.guild_id, self.bot.server_locations_cache
                )
                if s_lat is not None and s_lon is not None:
                    target_lat = s_lat
                    target_lon = s_lon
                    effective_display = s_display_name if s_display_name else f"Lat: {s_lat:.2f}, Lon: {s_lon:.2f}"
                    full_location_desc = effective_display
            return target_lat, target_lon, effective_display, full_location_desc

    # Fetches AQI info
    @app_commands.command(name="aqi_info", description="Displays the meaning of AQI numbers.")
    async def aqi_info_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Air Quality Index (AQI) Categories",
            description="Understanding AQI values and their health implications.",
            color=discord.Color.blue()
        )
        embed.add_field(name="1 - Good", value="Air quality is considered satisfactory, and air pollution poses little or no risk.", inline=False)
        embed.add_field(name="2 - Fair", value="Air quality is acceptable; however, some pollutants may be a concern for a small number of people.", inline=False)
        embed.add_field(name="3 - Moderate", value="Air quality is acceptable; however, some pollutants may be a concern for a small number of people.", inline=False)
        embed.add_field(name="4 - Poor", value="Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.", inline=False)
        embed.add_field(name="5 - Very Poor", value="Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.", inline=False)
        embed.set_footer(text="Categories based on OpenWeatherMap AQI scale.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Fetches current AQI
    @app_commands.command(name="aqi_c", description="Fetches current air pollution.")
    async def aqi_slash_current(self, interaction: discord.Interaction, city: str = None, state_code: str = None, country_code: str = None):
        if not self.bot.config.OPENWEATHERMAP_API_KEY:
            await interaction.response.send_message("API key not configured.", ephemeral=True)
            return

        target_lat, target_lon, effective_display, full_location_desc_or_error = await self._get_effective_location(
            interaction, city, state_code, country_code
        )

        if target_lat is None or target_lon is None: # Error occurred in _get_effective_location
            await interaction.response.send_message(full_location_desc_or_error, ephemeral=True)
            return

        await interaction.response.send_message(f"Fetching current air pollution data for **{full_location_desc_or_error}**...", ephemeral=False)

        aqi_params = {"lat": target_lat, "lon": target_lon, "appid": self.bot.config.OPENWEATHERMAP_API_KEY}
        aqi_data = await utils.make_api_request(self.bot.config.AIR_POLLUTION_CURRENT_API_URL, aqi_params)

        if aqi_data and "list" in aqi_data and aqi_data["list"]:
            current_entry = aqi_data["list"][0]
            aqi_index = current_entry.get("main", {}).get("aqi", "N/A")
            components = current_entry.get("components", {})
            dt_timestamp = current_entry.get("dt")

            current_date_str = "N/A"
            if dt_timestamp:
                local_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc).astimezone()
                current_date_str = local_datetime.strftime('%B %d, %Y')

            aqi_category = utils.get_aqi_category(aqi_index)
            
            embed_color = discord.Color.blue()
            if isinstance(aqi_index, int):
                colors = {1: discord.Color.green(), 2: discord.Color.yellow(), 3: discord.Color.orange(), 4: discord.Color.red(), 5: discord.Color.purple()}
                embed_color = colors.get(aqi_index, discord.Color.blue())

            embed = discord.Embed(
                title=f"Current Air Pollution for {effective_display}",
                description=f"Air Quality Index for Today ({current_date_str})",
                color=embed_color
            )
            embed.set_footer(text="Air quality data provided by OpenWeatherMap")
            embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)

            components_text_parts = []
            pollutants_map = {
                "co": {"name": "CO", "unit": "µg/m³"}, "no": {"name": "NO", "unit": "µg/m³"},
                "no2": {"name": "NO₂", "unit": "µg/m³"}, "o3": {"name": "O₃", "unit": "µg/m³"},
                "so2": {"name": "SO₂", "unit": "µg/m³"}, "pm2_5": {"name": "PM₂.₅", "unit": "µg/m³"},
                "pm10": {"name": "PM₁₀", "unit": "µg/m³"}, "nh3": {"name": "NH₃", "unit": "µg/m³"}
            }
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
            await interaction.edit_original_response(content=f"Could not retrieve current AQI for **{effective_display}**.", embed=None)

    # fetch AQI forecast
    @app_commands.command(name="aqi_f", description="Fetches air pollution forecast.")
    async def aqi_slash_forecast(self, interaction: discord.Interaction, city: str = None, state_code: str = None, country_code: str = None):
        """
        Fetches and displays air pollution forecast.
        Uses server-specific location if set, then global default, or provided location.
        """
        if not self.bot.config.OPENWEATHERMAP_API_KEY:
            await interaction.response.send_message(
                "Sorry, the API key for OpenWeatherMap air quality data is not configured. Please contact the bot administrator.",
                ephemeral=True
            )
            return

        target_lat, target_lon, effective_display, full_location_desc_or_error = await self._get_effective_location(
            interaction, city, state_code, country_code
        )

        if target_lat is None or target_lon is None: 
            await interaction.response.send_message(full_location_desc_or_error, ephemeral=True)
            return

        await interaction.response.send_message(f"Fetching air pollution forecast for **{full_location_desc_or_error}**...", ephemeral=False)

        aqi_params = {
            "lat": target_lat,
            "lon": target_lon,
            "appid": self.bot.config.OPENWEATHERMAP_API_KEY
        }

        aqi_data = await utils.make_api_request(self.bot.config.AIR_POLLUTION_FORECAST_API_URL, aqi_params)

        if aqi_data and "list" in aqi_data and aqi_data["list"]:
            selected_forecast_entry = None
            now_local = datetime.datetime.now().astimezone()
            tomorrow_local_date = (now_local + datetime.timedelta(days=1)).date()

            # iterate through forecast entries
            for entry in aqi_data["list"]:
                dt_timestamp = entry.get("dt")
                if dt_timestamp:
                    # convert Unix timestamp to a timezone-aware datetime object in UTC, then to local timezone
                    entry_local_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc).astimezone(now_local.tzinfo)
                    if entry_local_datetime.date() == tomorrow_local_date:
                        # if it's the first entry for tomorrow or closer to noon than a previously selected one
                        if selected_forecast_entry is None or \
                           abs(entry_local_datetime.hour - 12) < \
                           abs(datetime.datetime.fromtimestamp(selected_forecast_entry.get("dt"), tz=datetime.timezone.utc).astimezone(now_local.tzinfo).hour - 12):
                            selected_forecast_entry = entry
            
            # if no entry found for tomorrow, find the next available future entry
            if not selected_forecast_entry:
                now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
                future_entries = [e for e in aqi_data["list"] if e.get("dt", 0) > now_ts]
                if future_entries:
                    selected_forecast_entry = future_entries[0] 

            if not selected_forecast_entry:
                await interaction.edit_original_response(content=f"Could not find a suitable air quality forecast for **{effective_display}** in the API response.")
                return

            aqi_index = selected_forecast_entry.get("main", {}).get("aqi", "N/A")
            components = selected_forecast_entry.get("components", {})
            dt_timestamp = selected_forecast_entry.get("dt")

            forecast_date_str = "N/A"
            if dt_timestamp:
                # Convert to local time for display
                utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
                local_datetime_display = utc_datetime.astimezone(now_local.tzinfo) 
                forecast_date_str = local_datetime_display.strftime('%B %d, %Y at %I:%M %p %Z')

            aqi_category = utils.get_aqi_category(aqi_index)
            
            embed_color = discord.Color.blue()
            if isinstance(aqi_index, int):
                colors = {1: discord.Color.green(), 2: discord.Color.yellow(), 3: discord.Color.orange(), 4: discord.Color.red(), 5: discord.Color.purple()}
                embed_color = colors.get(aqi_index, discord.Color.blue())

            embed = discord.Embed(
                title=f"Air Pollution Forecast for {effective_display}",
                description=f"Forecast for: {forecast_date_str}",
                color=embed_color
            )
            embed.set_footer(text="Air quality data provided by OpenWeatherMap")
            embed.add_field(name="💨 Air Quality Index (AQI)", value=f"{aqi_index} - {aqi_category}", inline=False)

            components_text_parts = []
            # Using the same pollutant map as aqi_c for consistency
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
            error_message_content = f"Could not retrieve air quality forecast for **{effective_display}**."
            if aqi_data and "message" in aqi_data:
                error_message_content += f" API Message: {aqi_data['message']}"
            else:
                error_message_content += " Please check bot logs for more details or try again later."
            await interaction.edit_original_response(content=error_message_content, embed=None)


    @app_commands.command(name="weather", description="Fetches current weather.")
    async def weather_slash(self, interaction: discord.Interaction, city: str = None, state_code: str = None, country_code: str = None):
        """
        Fetches and displays current weather.
        Uses server-specific location if set, then global default, or provided location.
        """
        if not self.bot.config.OPENWEATHERMAP_API_KEY:
            await interaction.response.send_message(
                "Sorry, the API key for OpenWeatherMap weather data is not configured. Please contact the bot administrator.",
                ephemeral=True
            )
            return

        target_lat, target_lon, effective_display, full_location_desc_or_error = await self._get_effective_location(
            interaction, city, state_code, country_code
        )

        if target_lat is None or target_lon is None: # Error occurred in _get_effective_location
            await interaction.response.send_message(full_location_desc_or_error, ephemeral=True)
            return

        await interaction.response.send_message(f"Fetching current weather data for **{full_location_desc_or_error}**...", ephemeral=False)

        weather_params = {
            "lat": target_lat,
            "lon": target_lon,
            "appid": self.bot.config.OPENWEATHERMAP_API_KEY,
            "units": "metric" 
        }

        weather_data = await utils.make_api_request(self.bot.config.CURRENT_WEATHER_API_URL, weather_params)

        if weather_data and "main" in weather_data and "weather" in weather_data and weather_data["weather"]:
            main_data = weather_data["main"]
            weather_description_data = weather_data["weather"][0]
            
            description = weather_description_data.get("description", "N/A").capitalize()
            icon_code = weather_description_data.get("icon")
            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else None

            temp_kelvin = main_data.get("temp", "N/A")
            feels_like_kelvin = main_data.get("feels_like", "N/A")
            humidity = main_data.get("humidity", "N/A")
            pressure = main_data.get("pressure", "N/A") # hPa
            wind_speed = weather_data.get("wind", {}).get("speed", "N/A") # m/s
            visibility = weather_data.get("visibility", "N/A") # meters

            dt_timestamp = weather_data.get("dt")
            current_date_str = "N/A"
            if dt_timestamp:
                # Convert to local time for display
                now_local = datetime.datetime.now().astimezone() # Get current local timezone
                utc_datetime = datetime.datetime.fromtimestamp(dt_timestamp, tz=datetime.timezone.utc)
                local_datetime_display = utc_datetime.astimezone(now_local.tzinfo)
                current_date_str = local_datetime_display.strftime('%B %d, %Y at %I:%M %p %Z')

            # convert Kelvin to Celsius and Fahrenheit for user convenience
            temp_celsius, temp_fahrenheit = "N/A", "N/A"
            if isinstance(temp_kelvin, (int, float)):
                temp_celsius = temp_kelvin - 273.15
                temp_fahrenheit = temp_celsius * 9/5 + 32
            
            feels_like_celsius, feels_like_fahrenheit = "N/A", "N/A"
            if isinstance(feels_like_kelvin, (int, float)):
                feels_like_celsius = feels_like_kelvin - 273.15
                feels_like_fahrenheit = feels_like_celsius * 9/5 + 32


            embed = discord.Embed(
                title=f"Current Weather for {effective_display}",
                description=f"*{description}*",
                color=discord.Color.blue()
            )
            if icon_url:
                embed.set_thumbnail(url=icon_url)
            
            embed.add_field(name="🌡️ Temperature", 
                            value=(f"{temp_celsius:.1f}°C / {temp_fahrenheit:.1f}°F\n"
                                   f"(Feels like: {feels_like_celsius:.1f}°C / {feels_like_fahrenheit:.1f}°F)" 
                                   if isinstance(temp_celsius, float) else "N/A"), 
                            inline=False)
            embed.add_field(name="💧 Humidity", value=f"{humidity}%" if humidity != "N/A" else "N/A", inline=True)
            embed.add_field(name="🌬️ Wind", value=f"{wind_speed} m/s" if wind_speed != "N/A" else "N/A", inline=True)
            embed.add_field(name="📊 Pressure", value=f"{pressure} hPa" if pressure != "N/A" else "N/A", inline=True)
            if visibility != "N/A":
                 embed.add_field(name="👁️ Visibility", value=f"{visibility/1000:.1f} km" if isinstance(visibility, (int,float)) else "N/A", inline=True)


            if "sunrise" in weather_data.get("sys", {}) and "sunset" in weather_data.get("sys", {}):
                sunrise_ts = weather_data["sys"]["sunrise"]
                sunset_ts = weather_data["sys"]["sunset"]
                now_local = datetime.datetime.now().astimezone() 
                sunrise_local = datetime.datetime.fromtimestamp(sunrise_ts, tz=datetime.timezone.utc).astimezone(now_local.tzinfo)
                sunset_local = datetime.datetime.fromtimestamp(sunset_ts, tz=datetime.timezone.utc).astimezone(now_local.tzinfo)
                embed.add_field(name="☀️ Sunrise", value=sunrise_local.strftime('%I:%M %p %Z'), inline=True)
                embed.add_field(name="🌙 Sunset", value=sunset_local.strftime('%I:%M %p %Z'), inline=True)

            embed.set_footer(text=f"Data observed around: {current_date_str}\nWeather data provided by OpenWeatherMap")
            
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            error_message_content = f"Could not retrieve current weather data for **{effective_display}**."
            if weather_data and "message" in weather_data:
                error_message_content += f" API Message: {weather_data['message']}"
            else:
                error_message_content += " Please check bot logs for more details or try again later."
            await interaction.edit_original_response(content=error_message_content, embed=None)

async def setup(bot: commands.Bot):
    await bot.add_cog(WeatherCog(bot))
    print("WeatherCog loaded.")