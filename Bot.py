import os
import discord
import random
import logging
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
intents.guilds = True             # Enable access to guilds (for slash commands)

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)

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

# Function to truncate long deleted messages
def truncate_message(content, max_length=100):
    return content if len(content) <= max_length else content[:max_length] + '...'

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

            # Ensure we have at least two members to ship
            if len(eligible_members) < 2:
                await interaction.followup.send("Not enough eligible members to ship!", ephemeral=True)
                return

            # Shuffle the list once and select two random members
            random.shuffle(eligible_members)
            person1, person2 = eligible_members[:2]

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
            "**/help**: Show this help message."
        )
        await interaction.response.send_message(commands_list, ephemeral=True)

# Event listener for when a message is deleted
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
            f"🔴 {message.author.mention} just deleted a message: '{truncate_message(message.content)}' {reply_info} "
            f"in {message.channel.mention}."
        )

        await message.channel.send(deleted_message_info)

    except Exception as e:
        logging.error(f"Error in on_message_delete event: {e}")

# Event when the bot is ready
@bot.event
async def on_ready():
    try:
        logging.info(f'Logged in as {bot.user}!')

        # Sync commands with all the guilds the bot is in
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
            logging.info(f"Slash commands synced for guild {guild.id}: {guild.name}")

    except Exception as e:
        logging.error(f"Error during on_ready: {e}")

# Event listener for when a member joins the server
@bot.event
async def on_member_join(member):
    logging.info(f"New member joined: {member.name} in {member.guild.name}")

# Event listener for when a member leaves the server
@bot.event
async def on_member_remove(member):
    logging.info(f"Member left: {member.name} in {member.guild.name}")

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

        # Force sync after adding the cog
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)

    except Exception as e:
        logging.error(f"Error adding cog: {e}")

# Assign the setup_hook directly to the bot object
bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
