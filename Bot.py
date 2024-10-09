import os
import discord
import random
import logging
import aiohttp
import json
from discord import app_commands
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.INFO)

# Retrieve the bot token from Render's environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Role ID for restricted commands
RESTRICTED_ROLE_ID = 1292555408724066364

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

# Persistent marriage storage file
MARRIAGES_FILE = "marriages.json"

# In-memory marriage storage
marriages = {}

# Load marriages from the file at startup
def load_marriages():
    global marriages
    try:
        with open(MARRIAGES_FILE, 'r') as f:
            marriages = json.load(f)
            logging.info("Marriages loaded from file.")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("No existing marriage file found or invalid data. Starting fresh.")
        marriages = {}

# Save marriages to a file
def save_marriages():
    try:
        with open(MARRIAGES_FILE, 'w') as f:
            json.dump(marriages, f, indent=4)
            logging.info("Marriages saved to file.")
    except Exception as e:
        logging.error(f"Error saving marriages: {e}")

# Custom messages for different compatibility percentage ranges
def get_custom_message(compatibility_percentage):
    if compatibility_percentage < 25:
        return random.choice([
            "These two should never be matched! 😬",
            "This is a disaster waiting to happen! 😱",
            "No chance! 😅",
            "Run away before it's too late! 🏃‍♂️💨"
        ])
    elif compatibility_percentage < 50:
        return random.choice([
            "It’s not looking good for these two... 😅",
            "Maybe, but probably not! 😕",
            "They might get along… in an alternate universe. 🌍",
            "This ship is leaking water. 🛳️💧"
        ])
    elif compatibility_percentage < 75:
        return random.choice([
            "There might be something here! 😉",
            "They could make it work with some effort! 🛠️",
            "A promising pair, but it needs some work! 😄",
            "They are on the right path! 🌟"
        ])
    elif compatibility_percentage < 90:
        return random.choice([
            "This pair is looking quite promising! 😍",
            "There's definite chemistry here! 💥",
            "These two are getting close to perfect! ✨",
            "They are almost a perfect match! ❤️"
        ])
    else:
        return random.choice([
            "They are a match made in heaven! 💖",
            "This is true love! 💘",
            "It doesn’t get better than this! 🌟",
            "This is the ultimate ship! 🚢💞"
        ])

# Excluded users (by ID and username)
EXCLUDED_USER_IDS = [743263377773822042]
EXCLUDED_USER_NAMES = ["lovee_ariana", "Ari"]

# Special user IDs for guaranteed 100% compatibility
ZEKE_ID = 123456789  # Replace with Zeeke's actual ID
ALLIE_ID = 987654321  # Replace with Allie's actual ID

# Restrict command access to a specific role with improved error message
def has_restricted_role():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, id=RESTRICTED_ROLE_ID)
        if role:
            return True
        role_name = discord.utils.get(interaction.guild.roles, id=RESTRICTED_ROLE_ID).name
        await interaction.response.send_message(f"You need the '{role_name}' role to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Define the cog for application commands
class MyBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Register the ship command (accessible by anyone)
    @app_commands.command(name="ship", description="Ship two random members together with a love score!")
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.user.id))  # 1 minute cooldown
    async def ship(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            eligible_members = [
                member for member in interaction.guild.members 
                if not member.bot and member.id not in EXCLUDED_USER_IDS and member.display_name not in EXCLUDED_USER_NAMES
            ]

            zeeke = discord.utils.get(interaction.guild.members, id=ZEKE_ID)
            allie = discord.utils.get(interaction.guild.members, id=ALLIE_ID)

            if zeeke and allie:
                eligible_members.extend([zeeke, allie] * 10)  # Add them 10 times to increase their chance

            if len(eligible_members) < 2:
                await interaction.followup.send("Not enough eligible members to ship!", ephemeral=True)
                return

            random.shuffle(eligible_members)
            person1, person2 = eligible_members[:2]

            if ((person1.id == ZEKE_ID and person2.id == ALLIE_ID) or
                (person1.id == ALLIE_ID and person2.id == ZEKE_ID)):
                compatibility_percentage = 100
                custom_message = "These two are a match made in heaven! 💖"
            else:
                compatibility_percentage = random.randint(0, 100)
                custom_message = get_custom_message(compatibility_percentage)

            await interaction.followup.send(
                f"{person1.mention} and {person2.mention} have a {compatibility_percentage}% compatibility! 💘\n{custom_message}"
            )

            logging.info(f"{interaction.user.name} used /ship to match {person1.name} and {person2.name}.")

        except Exception as e:
            logging.error(f"Error in /ship command: {e}")
            await interaction.followup.send("An error occurred while processing the ship command. Please try again later.", ephemeral=True)

    # Copy a user's profile with rate limiting (restricted by role)
    @app_commands.command(name="copy", description="Copy another user's profile including name and profile picture.")
    @has_restricted_role()
    @app_commands.checks.cooldown(1, 600, key=lambda i: (i.user.id))  # 10 minute cooldown
    async def copy(self, interaction: discord.Interaction, target: discord.Member):
        global original_bot_name, original_bot_avatar, original_bot_status, session

        if original_bot_name is None:
            original_bot_name = bot.user.name
        if original_bot_avatar is None:
            original_bot_avatar = await bot.user.avatar.read() if bot.user.avatar else None
        if original_bot_status is None:
            original_bot_status = bot.activity

        try:
            await interaction.response.defer()  # Acknowledge the interaction before any long-running tasks

            target_name = target.display_name
            target_avatar_url = target.avatar.url if target.avatar else None
            target_status = target.activity.name if target.activity else "No status"

            # Change the bot's name
            try:
                await bot.user.edit(username=target_name)
            except discord.errors.HTTPException as e:
                logging.error(f"Error changing bot name: {e}")
                await interaction.followup.send(f"Failed to copy {target.mention}'s name due to rate limits. Please try again later.", ephemeral=True)
                return

            # Change the bot's avatar if the user has one
            if target_avatar_url:
                try:
                    async with session.get(target_avatar_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            await bot.user.edit(avatar=data)
                except discord.errors.HTTPException as e:
                    logging.error(f"Error changing bot avatar: {e}")
                    await interaction.followup.send(f"Failed to copy {target.mention}'s avatar due to rate limits. Please try again later.", ephemeral=True)
                    return

            # Update the bot's status with the user's activity (if they have one)
            await bot.change_presence(activity=discord.Game(name=target_status))

            # Notify success
            await interaction.followup.send(f"Copied {target.mention}'s profile successfully!", ephemeral=True)

        except Exception as e:
            logging.error(f"Error in /copy command: {e}")
            await interaction.followup.send(f"Failed to copy {target.mention}'s profile.", ephemeral=True)

    # Revert bot's profile (restricted by role)
    @app_commands.command(name="stop", description="Revert the bot back to its original profile.")
    @has_restricted_role()
    async def stop(self, interaction: discord.Interaction):
        global original_bot_name, original_bot_avatar, original_bot_status

        try:
            if original_bot_name:
                await bot.user.edit(username=original_bot_name)
            if original_bot_avatar:
                await bot.user.edit(avatar=original_bot_avatar)
            if original_bot_status:
                await bot.change_presence(activity=original_bot_status)

            await interaction.response.send_message("Reverted back to the original profile!", ephemeral=True)
            logging.info(f"{interaction.user.name} used /stop to revert the bot's profile.")

        except Exception as e:
            logging.error(f"Error in /stop command: {e}")
            await interaction.response.send_message("Failed to revert back to the original profile.", ephemeral=True)

    # Marry command: Marry two people and store the marriage
    @app_commands.command(name="marry", description="Marry two people.")
    async def marry(self, interaction: discord.Interaction, person1: discord.Member, person2: discord.Member):
        try:
            # Ensure they are not already married
            if (person1.id, person2.id) in marriages or (person2.id, person1.id) in marriages:
                await interaction.response.send_message(f"{person1.mention} and {person2.mention} are already married!", ephemeral=True)
                return

            # Store the marriage
            marriages[(person1.id, person2.id)] = (person1.display_name, person2.display_name)
            save_marriages()  # Save marriages after adding

            # Send a marriage message
            await interaction.response.send_message(f"🎉 {person1.mention} and {person2.mention} just got married! 💍")

            logging.info(f"{person1.display_name} and {person2.display_name} got married.")

        except Exception as e:
            logging.error(f"Error in /marry command: {e}")
            await interaction.response.send_message("An error occurred while processing the marriage.", ephemeral=True)

    # Check marriages command: List all current marriages
    @app_commands.command(name="check_marriages", description="Check all current marriages.")
    async def check_marriages(self, interaction: discord.Interaction):
        try:
            if not marriages:
                await interaction.response.send_message("There are no current marriages.", ephemeral=True)
                return

            # Create a list of all marriages
            marriage_list = "\n".join([f"{p1} ❤ {p2}" for (_, (p1, p2)) in marriages.items()])
            await interaction.response.send_message(f"Here are the current marriages:\n\n{marriage_list}", ephemeral=True)

            logging.info("Checked marriages.")

        except Exception as e:
            logging.error(f"Error in /check_marriages command: {e}")
            await interaction.response.send_message("An error occurred while checking marriages.", ephemeral=True)

    # Remove marriage command: Divorce two people and remove the marriage
    @app_commands.command(name="remove_marriage", description="Remove a marriage.")
    async def remove_marriage(self, interaction: discord.Interaction, person1: discord.Member, person2: discord.Member):
        try:
            # Check if the two people are married
            if (person1.id, person2.id) in marriages:
                del marriages[(person1.id, person2.id)]
            elif (person2.id, person1.id) in marriages:
                del marriages[(person2.id, person1.id)]
            else:
                await interaction.response.send_message(f"{person1.mention} and {person2.mention} are not married!", ephemeral=True)
                return

            save_marriages()  # Save marriages after removal

            # Send a divorce message
            await interaction.response.send_message(f"💔 {person1.mention} and {person2.mention} are no longer married.")

            logging.info(f"{person1.display_name} and {person2.display_name} are no longer married.")

        except Exception as e:
            logging.error(f"Error in /remove_marriage command: {e}")
            await interaction.response.send_message("An error occurred while removing the marriage.", ephemeral=True)

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
        logging.info(f"{message.author.name} deleted a message in {message.channel.name}: '{message.content}'")

    except Exception as e:
        logging.error(f"Error in on_message_delete event: {e}")

# Event when the bot is ready
@bot.event
async def on_ready():
    global session
    try:
        logging.info(f'Logged in as {bot.user}!')

        session = aiohttp.ClientSession()

        # Load marriages from file at startup
        load_marriages()

        await bot.change_presence(activity=discord.Game(name="Shipping Members"))

        await bot.tree.sync()
        logging.info("Slash commands globally synced.")

    except Exception as e:
        logging.error(f"Error during on_ready: {e}")

# Clean up session when bot closes
@bot.event
async def on_shutdown():
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

        await bot.tree.sync()
        logging.info("Global slash commands synced.")

    except Exception as e:
        logging.error(f"Error adding cog: {e}")

bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
