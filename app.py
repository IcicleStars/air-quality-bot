# main file
import discord
from discord.ext import commands
import os

# other py files
import config
import utils

# define intents
intents = discord.Intents.default()

# bot instance
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='e!', intents=intents)
        # attach config to bot instance
        self.config = config
        self.server_locations_cache = {}

    async def setup_hook(self):
        # Load server locations early
        self.server_locations_cache = utils.load_server_locations_from_file(self.config.LOCATIONS_FILE)
        print(f"Loaded server locations: {self.server_locations_cache}")

        # load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Successfully loaded extension: cogs.{filename[:-3]}")
                except Exception as e:
                    print(f"Failed to load extension cogs.{filename[:-3]}: {e}")

        # sync commands !!!!!
        if self.config.TEST_GUILD_ID:
            guild = discord.Object(id=self.config.TEST_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s) to test guild: {self.config.TEST_GUILD_ID}")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s) globally.")

    # bot connected
    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')
        print(f'Bot ID: {self.user.id}')

        # checks for api key
        if not self.config.OPENWEATHERMAP_API_KEY:
            print("WARNING: 'API_KEY' for OpenWeatherMap is not set. Weather/AQI commands may fail.")
        else:
            key_preview = self.config.OPENWEATHERMAP_API_KEY[:5] + "..." + self.config.OPENWEATHERMAP_API_KEY[-5:] \
                          if len(self.config.OPENWEATHERMAP_API_KEY) > 10 else self.config.OPENWEATHERMAP_API_KEY
            print(f"OpenWeatherMap API Key loaded: {key_preview}")

# bot
bot = MyBot()

# run bot
if __name__ == "__main__":
    if not config.TOKEN:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN is not set in config.py or .env file. Bot cannot start.")
        exit()
    
    bot.run(config.TOKEN)