import os
import discord
import random
import logging
import aiohttp
import json
import yt_dlp
import asyncio
from discord import app_commands
from discord.ext import commands
from discord import FFmpegPCMAudio

# Set up logging
logging.basicConfig(level=logging.INFO)

# Retrieve the bot token from Render's environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Role IDs for restricted commands
ALLOWED_ROLE_IDS = [1292555279246032916, 1292555408724066364]

# Enable all intents including the privileged ones
intents = discord.Intents.default()
intents.members = True            # Enable access to server members
intents.message_content = True    # Enable access to message content
intents.voice_states = True       # Enable access to voice states

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents, reconnect=True)

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

# Excluded users (by ID and username)
EXCLUDED_USER_IDS = [743263377773822042]
EXCLUDED_USER_NAMES = ["lovee_ariana", "Ari"]

# Special user IDs for guaranteed 100% compatibility
ZEKE_ID = 123456789  # Replace with Zeeke's actual ID
ALLIE_ID = 987654321  # Replace with Allie's actual ID

# Restrict command access to specific roles
def has_restricted_roles():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = ALLOWED_ROLE_IDS  # List of allowed role IDs
        user_roles = [role.id for role in interaction.user.roles]
        
        if any(role_id in user_roles for role_id in allowed_roles):
            return True
        
        # Send an error message if the user doesn't have the required role
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Play a song from a URL (YouTube or Spotify link)
async def play_song(interaction, url):
    # Join the user's voice channel if not already in one
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel to play music!", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    if interaction.guild.voice_client is None:
        voice_client = await voice_channel.connect()
    else:
        voice_client = interaction.guild.voice_client

    # Defer the interaction to avoid timeouts
    await interaction.response.defer()

    # Use yt-dlp to get audio stream URL from YouTube link, skipping sign-in-required videos
    try:
        ydl_opts = {
            'format': 'bestaudio',
            'noplaylist': True,
            'ignoreerrors': True,  # Skip videos that raise errors
            'extract_flat': True,  # Avoid downloading video details that require login
            'age_limit': 0,  # Do not allow age-restricted content
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Could not extract video information.")
            audio_url = info.get('url', None)
            title = info.get('title', 'Unknown Song')

        if not audio_url:
            raise Exception("No playable audio found.")

        # Play the audio
        source = FFmpegPCMAudio(audio_url)
        voice_client.play(source, after=lambda e: logging.info(f'Finished playing {title}.'))

        await interaction.followup.send(f"Now playing: {title}", ephemeral=False)
        logging.info(f"Playing {title} from {url} in {voice_channel.name}")

    except yt_dlp.utils.ExtractorError as e:
        if 'Sign in to confirm you’re not a bot' in str(e):
            logging.error(f"Error playing song from {url}: Age-restricted or login required")
            await interaction.followup.send("The video is age-restricted or requires a login. Please use another link.", ephemeral=True)
        else:
            logging.error(f"Error playing song from {url}: {e}")
            await interaction.followup.send("Failed to play the song. Make sure the URL is valid or the video is public.", ephemeral=True)

    except Exception as e:
        logging.error(f"Error playing song from {url}: {e}")
        await interaction.followup.send("Failed to play the song. Make sure the URL is valid or the video is public.", ephemeral=True)

# Stop playing and disconnect from the voice channel
async def stop_play(interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is not None and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
        await interaction.response.send_message("Stopped playing and left the voice channel.", ephemeral=False)
        logging.info(f"Bot left the voice channel: {voice_client.channel.name}")
    else:
        await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)

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

    # Copy a user's profile with rate limiting (restricted by roles)
    @app_commands.command(name="copy", description="Copy another user's profile including name and profile picture.")
    @has_restricted_roles()  # Apply the role restriction
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

    # Revert bot's profile (restricted by roles)
    @app_commands.command(name="stop", description="Revert the bot back to its original profile.")
    @has_restricted_roles()  # Apply the role restriction
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

    # Marry command (restricted by roles)
    @app_commands.command(name="marry", description="Marry two people.")
    @has_restricted_roles()  # Apply the role restriction
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

    # Remove marriage command (restricted by roles)
    @app_commands.command(name="remove_marriage", description="Remove a marriage.")
    @has_restricted_roles()  # Apply the role restriction
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

    # Check marriages command: List all current marriages (accessible by everyone)
    @app_commands.command(name="check_marriages", description="Check all current marriages.")
    async def check_marriages(self, interaction: discord.Interaction):
        try:
            if not marriages:
                await interaction.response.send_message("There are no current marriages.", ephemeral=True)
                return

            # Create a list of all marriages
            marriage_list = "\n".join([f"{p1} ❤ {p2}" for (_, (p1, p2)) in marriages.items()])
            await interaction.response.send_message(f"Here are the current marriages:\n\n{marriage_list}", ephemeral=False)

            logging.info("Checked marriages.")

        except Exception as e:
            logging.error(f"Error in /check_marriages command: {e}")
            await interaction.response.send_message("An error occurred while checking marriages.", ephemeral=True)

    # Send message command (restricted by roles)
    @app_commands.command(name="send_message", description="Send a message to a specific channel.")
    @has_restricted_roles()  # Apply the role restriction
    async def send_message(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        try:
            await channel.send(message)
            await interaction.response.send_message(f"Message sent to {channel.mention}", ephemeral=True)
            logging.info(f"{interaction.user.name} sent a message to {channel.name}: {message}")

        except Exception as e:
            logging.error(f"Error in /send_message command: {e}")
            await interaction.response.send_message("An error occurred while sending the message.", ephemeral=True)

    # Play command for playing Spotify/YouTube songs
    @app_commands.command(name="play", description="Play a song from a Spotify or YouTube link.")
    async def play(self, interaction: discord.Interaction, url: str):
        await play_song(interaction, url)

    # Stop play command to stop the music and leave the voice channel
    @app_commands.command(name="stop_play", description="Stop the music and make the bot leave the voice channel.")
    async def stop_play_cmd(self, interaction: discord.Interaction):
        await stop_play(interaction)

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

# Handle bot reconnection
@bot.event
async def on_disconnect():
    logging.warning("Bot disconnected. Attempting to reconnect...")

@bot.event
async def on_resumed():
    logging.info("Bot successfully resumed the session.")

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
