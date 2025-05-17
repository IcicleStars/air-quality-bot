# Imports
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Initialize env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('TEST_GUILD_ID'))

intents = discord.Intents.default()
intents.message_content = True

# Create instance of bot
bot = commands.Bot(command_prefix='e!', intents=intents)

# bot connection event
@bot.event
async def on_ready():
    """Prints a message to the terminal when the bot is successfully connected."""
    print(f'{bot.user.name} connected')
    print(f'Connected to: {bot.get_guild(GUILD_ID).name} (ID: {GUILD_ID})')
    try:
        
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands to guild {GUILD_ID}.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# PREFIX COMMANDS BELOW

@bot.command(name='hello', description='Says hello!')
async def hello(ctx):
    """A simple command that says hello."""
    await ctx.send(f'Hello {ctx.author.mention}!')

# SLASH COMMANDS BELOW

# Practice command (slash command)
@bot.tree.command(name="hello", description="Says hello!", guild=discord.Object(id=GUILD_ID))
async def hello(interaction: discord.Interaction):
    """A simple slash command that says hello."""
    await interaction.response.send_message(f"Hello {interaction.user.mention}!", ephemeral=True)

# Run bot
if __name__ == "__main__":
    if TOKEN is None:
        print("Error: DISCORD_BOT_TOKEN is not set in the .env file.")
    else:
        bot.run(TOKEN)