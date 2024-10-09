import os
import discord
import random
import logging
import aiohttp
from discord import app_commands
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.INFO)

# Retrieve the bot token from Render's environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Check if DISCORD_TOKEN is present
if not DISCORD_TOKEN:
    logging.error("DISCORD_TOKEN not found! Make sure it's set in your environment variables.")
    exit(1)

# Enable all intents including the privileged ones
intents = discord.Intents.default()
intents.members = True            # Enable access to server members
intents.message_content = True    # Enable access to message content

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Store the bot's original information to revert later
original_bot_name = None
original_bot_avatar = None
original_bot_status = None
session = None  # aiohttp session, initialized in on_ready()

# Custom messages for different compatibility percentage ranges
def get_custom_message(compatibility_percentage):
    if compatibility_percentage < 25:
        messages = [
            "These two should never be matched! 😬",
            "This is a disaster waiting to happen! 😱",
            "No chance! 😅",
            "Run away before it's too late! 🏃‍♂️💨"
        ]
    elif compatibility_percentage < 50:
        messages = [
            "It’s not looking good for these two... 😅",
            "Maybe, but probably not! 😕",
            "They might get along… in an alternate universe. 🌍",
            "This ship is leaking water. 🛳️💧"
        ]
    elif compatibility_percentage < 75:
        messages = [
            "There might be something here! 😉",
            "They could make it work with some effort! 🛠️",
            "A promising pair, but it needs some work! 😄",
            "They are on the right path! 🌟"
        ]
    elif compatibility_percentage < 90:
        messages = [
            "This pair is looking quite promising! 😍",
            "There's definite chemistry here! 💥",
            "These two are getting close to perfect! ✨",
            "They are almost a perfect match! ❤️"
        ]
    else:
        messages = [
            "They are a match made in heaven! 💖",
            "This is true love! 💘",
            "It doesn’t get better than this! 🌟",
            "This is the ultimate ship! 🚢💞"
        ]
    
    return random.choice(messages)

# Excluded users (by ID and username)
EXCLUDED_USER_IDS = [743263377773822042]
EXCLUDED_USER_NAMES = ["lovee_ariana", "Ari"]

# Special user IDs or display names for guaranteed 100% compatibility
ZEKE_ID = 123456789  # Replace with Zeeke's actual ID
ALLIE_ID = 987654321  # Replace with Allie's actual ID

# Define the cog for application commands
class MyBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Register the ship command
    @app_commands.command(name="ship", description="Ship two random members together with a love score!")
    async def ship(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            # Get the list of all members in the server excluding the specific users
            eligible_members = [
                member for member in interaction.guild.members 
                if not member.bot and 
                member.id not in EXCLUDED_USER_IDS and 
                member.display_name not in EXCLUDED_USER_NAMES
            ]

            # Add Zeeke and Allie multiple times to increase their chances
            zeeke = discord.utils.get(interaction.guild.members, id=ZEKE_ID)
            allie = discord.utils.get(interaction.guild.members, id=ALLIE_ID)

            if zeeke and allie:
                eligible_members.extend([zeeke, allie] * 10)  # Add them 10 times to increase their chance

            # Ensure we have at least two members to ship
            if len(eligible_members) < 2:
                await interaction.followup.send("Not enough eligible members to ship!", ephemeral=True)
                return

            # Shuffle the list once and select two random members
            random.shuffle(eligible_members)
            person1, person2 = eligible_members[:2]

            # Check if Zeeke and Allie are the chosen members
            if ((person1.id == ZEKE_ID and person2.id == ALLIE_ID) or
                (person1.id == ALLIE_ID and person2.id == ZEKE_ID)):
                # Always give them 100% compatibility
                compatibility_percentage = 100
                custom_message = "These two are a match made in heaven! 💖"
            else:
                # Generate a random compatibility percentage
                compatibility_percentage = random.randint(0, 100)
                # Get the custom message based on the compatibility percentage
                custom_message = get_custom_message(compatibility_percentage)

            # Send the ship result with the compatibility percentage and custom message
            await interaction.followup.send(
                f"{person1.mention} and {person2.mention} have a {compatibility_percentage}% compatibility! 💘\n{custom_message}"
            )

        except Exception as e:
            logging.error(f"Error in /ship command: {e}")
            await interaction.followup.send("An error occurred while processing the ship command. Please try again later.", ephemeral=True)

    # Register the help command
    @app_commands.command(name="help", description="Displays a list of available commands.")
    async def help_command(self, interaction: discord.Interaction):
        commands_list = (
            "**/ship**: Ship two random members together with a love score!\n"
            "**/copy**: Copy another user's profile (name, profile picture).\n"
            "**/stop**: Revert the bot to its original profile.\n"
            "**/help**: Show this help message."
        )
        await interaction.response.send_message(commands_list, ephemeral=True)

    # Copy a user's profile information
    @app_commands.command(name="copy", description="Copy another user's profile including name and profile picture")
    async def copy(self, interaction: discord.Interaction, target: discord.Member):
        global original_bot_name, original_bot_avatar, original_bot_status, session

        # Store the bot's original details before changing them
        if original_bot_name is None:
            original_bot_name = bot.user.name
        if original_bot_avatar is None:
            original_bot_avatar = await bot.user.avatar.read() if bot.user.avatar else None
        if original_bot_status is None:
            original_bot_status = bot.activity

        try:
            # Get the target's profile information
            target_name = target.display_name
            target_avatar_url = target.avatar.url if target.avatar else None
            target_status = target.activity.name if target.activity else "No status"

            # Change the bot's name
            await bot.user.edit(username=target_name)

            # Change the bot's avatar if the user has one
            if target_avatar_url:
                async with session.get(target_avatar_url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        await bot.user.edit(avatar=data)

            # Update the bot's status with the user's activity (if they have one)
            await bot.change_presence(activity=discord.Game(name=target_status))

            await interaction.response.send_message(f"Copied {target.mention}'s profile!", ephemeral=True)

        except Exception as e:
            logging.error(f"Error in /copy command: {e}")
            await interaction.response.send_message(f"Failed to copy {target.mention}'s profile.", ephemeral=True)

    # Stop command to revert back to the original profile
    @app_commands.command(name="stop", description="Revert the bot back to its original profile")
    async def stop(self, interaction: discord.Interaction):
        global original_bot_name, original_bot_avatar, original_bot_status

        try:
            # Revert the bot's name, avatar, and status
            if original_bot_name:
                await bot.user.edit(username=original_bot_name)
            if original_bot_avatar:
                await bot.user.edit(avatar=original_bot_avatar)
            if original_bot_status:
                await bot.change_presence(activity=original_bot_status)

            await interaction.response.send_message("Reverted back to the original profile!", ephemeral=True)

        except Exception as e:
            logging.error(f"Error in /stop command: {e}")
            await interaction.response.send_message("Failed to revert back to the original profile.", ephemeral=True)

# Message delete detection
@bot.event
async def on_message_delete(message):
    try:
        if message.author.bot:
            return

        reply_info = ""
        if message.reference and message.reference.resolved:
            replied_to = message.reference.resolved
            reply_info = f"(This was a reply to {replied_to.author.mention})"

        deleted_message_info = (
            f"🔴 {message.author.mention} just deleted a message: '{message.content}' {reply_info} "
            f"in {message.channel.mention}."
        )

        await message.channel.send(deleted_message_info)

    except Exception as e:
        logging.error(f"Error in on_message_delete event: {e}")

# Event when the bot is ready
@bot.event
async def on_ready():
    global session
    try:
        logging.info(f'Logged in as {bot.user}!')

        # Initialize aiohttp session
        session = aiohttp.ClientSession()

        # Sync commands globally (for all guilds)
        await bot.tree.sync()
        logging.info("Slash commands globally synced.")

    except Exception as e:
        logging.error(f"Error during on_ready: {e}")

# Clean up session when bot closes
@bot.event
async def on_close():
    global session
    if session:
        await session.close()

# Error handling for command errors
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist.", ephemeral=True)
    else:
        logging.error(f"Unexpected error: {error}")
        await ctx.send("An unexpected error occurred.", ephemeral=True)

# Add the cog to the bot and force command sync
async def setup_hook():
    try:
        await bot.add_cog(MyBot(bot))
        logging.info("Successfully added the MyBot cog.")

        # Global sync for all commands instead of per guild
        await bot.tree.sync()
        logging.info("Global slash commands synced.")

    except Exception as e:
        logging.error(f"Error adding cog: {e}")

# Assign the setup_hook directly to the bot object
bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
