import os
import discord
import logging
import aiohttp
from discord import app_commands
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.INFO)

# Retrieve the bot token from Render's environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# Role IDs for restricted commands
ALLOWED_ROLE_IDS = [1292555279246032916, 1292555408724066364]

# Enable all intents including the privileged ones
intents = discord.Intents.default()
intents.members = True  # Enable access to server members
intents.message_content = True  # Enable access to message content

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Restrict command access to specific roles
def has_restricted_roles():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = ALLOWED_ROLE_IDS
        user_roles = [role.id for role in interaction.user.roles]

        # Check if the user has any of the allowed roles
        if any(role_id in user_roles for role_id in allowed_roles):
            return True

        # If not, send an ephemeral response indicating no permission
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Send message command
@tree.command(name="send_message", description="Send a message to a specific channel.")
@has_restricted_roles()
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, *, message: str):
    try:
        await channel.send(message)
        await interaction.response.send_message(f"Message sent to {channel.mention}", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in /send_message command: {e}")
        await interaction.response.send_message("An error occurred while sending the message.", ephemeral=True)

# Detect deleted messages (ignores messages deleted by bots)
@bot.event
async def on_message_delete(message):
    # Ignore messages from bots or messages deleted by bots
    if message.author.bot or message.guild.me in message.mentions:
        return

    # Only proceed if the message was deleted in a guild (server)
    if message.guild and message.content:
        try:
            # Check if the deleted message was a reply to someone
            reply_info = ""
            if message.reference and message.reference.resolved:
                replied_user = message.reference.resolved.author
                reply_info = f"(This was a reply to {replied_user.mention})"

            # Send an embed with information about the deleted message
            embed = discord.Embed(
                title="Message Deleted",
                description=f"{message.author.mention} just deleted a message in {message.channel.mention}:\n\n'{message.content}' {reply_info}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)

        except discord.Forbidden:
            logging.error("Bot does not have permission to send messages in this channel.")
        except Exception as e:
            logging.error(f"Error sending deleted message log: {e}")

# Detect edited messages and log the change
@bot.event
async def on_message_edit(before, after):
    # Ignore edits from bots or if the content hasn't changed
    if before.author.bot or before.content == after.content:
        return

    # Only proceed if the message edit happened in a guild (server)
    if before.guild:
        try:
            # Send an embed with information about the edited message
            embed = discord.Embed(
                title="Message Edited",
                color=discord.Color.blue()
            )
            embed.add_field(name="Before", value=before.content, inline=False)
            embed.add_field(name="After", value=after.content, inline=False)
            embed.set_footer(text=f"Edited by {before.author.display_name} in #{before.channel}")

            await before.channel.send(embed=embed)

        except discord.Forbidden:
            logging.error("Bot does not have permission to send messages in this channel.")
        except Exception as e:
            logging.error(f"Error sending edited message log: {e}")

# Bot setup hook
async def setup_hook():
    global session
    session = aiohttp.ClientSession()
    logging.info("Bot setup complete.")

# Close the aiohttp session when the bot shuts down
@bot.event
async def on_close():
    if session:
        await session.close()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
