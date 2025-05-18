# cogs/settings_cog.py
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import MissingPermissions
from discord.app_commands.checks import has_permissions
import datetime

import utils 
import config

# SettingsCog class
class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # SET SERVER LOCATION
    @app_commands.command(name="setlocation", description="Sets default location for this server.")
    @has_permissions(manage_guild=True)
    async def set_location_slash(self, interaction: discord.Interaction, city: str, state_code: str = None, country_code: str = None):
        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        lat, lon, final_display_name_or_error = await utils.get_coordinates_from_api(
            city, state_code, country_code,
            self.bot.config.OPENWEATHERMAP_API_KEY,
            self.bot.config.GEOCODING_API_URL
        )

        if lat is None or lon is None:
            await interaction.followup.send(final_display_name_or_error, ephemeral=True)
            return

        self.bot.server_locations_cache[interaction.guild_id] = {
            "lat": lat,
            "lon": lon,
            "display_name": final_display_name_or_error, # final_display_name_or_error is display_name here
            "set_by_user_id": interaction.user.id,
            "set_at": datetime.datetime.now().isoformat()
        }
        utils.save_server_locations_to_file(self.bot.server_locations_cache, self.bot.config.LOCATIONS_FILE)

        await interaction.followup.send(
            f"Default location for this server has been set to: {final_display_name_or_error} (Lat: {lat:.4f}, Lon: {lon:.4f})",
            ephemeral=False
        )

    @set_location_slash.error
    async def set_location_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, MissingPermissions):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            error_message = f"An unexpected error occurred with setlocation: {error}"
            print(error_message) 
            # Check if response has already been sent or deferred
            if not interaction.response.is_done():
                await interaction.response.send_message("An unexpected error occurred. Please try again later.", ephemeral=True)
            else:
                await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
    print("SettingsCog loaded.")