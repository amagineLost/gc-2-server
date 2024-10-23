import os
import discord
import random
import logging
import aiohttp
import json
import asyncio
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
intents.messages = True  # Enable message-related events like deletion detection

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Store the bot's original information to revert later
original_bot_name = None
original_bot_avatar = None
original_bot_status = None
session = None  # aiohttp session, initialized in on_ready()

# Persistent marriage storage file
MARRIAGES_FILE = "marriages.json"

# In-memory marriage storage
marriages = {}

# Global flag to control the singing process
is_singing = False

# Dictionary to store multiple songs with titles as keys
SONG_LYRICS = {
    "pony club": [
        "I know you wanted me to stay",
        "But I can't ignore the visions of LA",
        "I’m dreaming of a new place and a new time",
        "Where every hill I climb is mine",
        "Oh, I’m heading to the pony club tonight",
        "Where the lights are shining bright",
        "Riding under neon skies",
        "I’m free, I’m alive",
        "Oh, I'm going to the pony club",
        "Just to prove that I can’t be stopped",
        "Oh, I'm going to the pony club",
        "To ride the dream, no matter the cost",
        "I’ll chase the thrill, under the city lights",
        "No more doubts, no more fights.",
        "I'm no longer a fool",
        "I'm just riding for the thrill."
    ],
    "after midnight": [
        "My mama said, 'Nothing good happens",
        "When it’s late and you’re on your own'",
        "But I can’t resist the afterglow",
        "I’m drawn to the night, I can’t say no",
        "Oh, after midnight, the world is mine",
        "I feel alive, I’m in my prime",
        "Oh, after midnight, I lose control",
        "But I find myself in the rhythm’s soul",
        "Lights are flashing, music’s loud",
        "I’m just one face in the crowd",
        "Oh, after midnight, I’m free to be wild",
        "Dancing alone but with a smile",
        "This is where I belong, where I shine",
        "Under the stars, feeling divine."
    ]
}

# Excluded users (by ID and username)
EXCLUDED_USER_IDS = [743263377773822042]
EXCLUDED_USER_NAMES = ["lovee_ariana", "Ari"]

# Special user IDs for guaranteed 100% compatibility
ZEKE_ID = 123456789  # Replace with Zeeke's actual ID
ALLIE_ID = 987654321  # Replace with Allie's actual ID

# Restrict command access to specific roles
def has_restricted_roles():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = ALLOWED_ROLE_IDS
        user_roles = [role.id for role in interaction.user.roles]

        if any(role_id in user_roles for role_id in allowed_roles):
            return True

        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# /8ball command
EIGHT_BALL_RESPONSES = [
    "It is certain.", "Without a doubt.", "Yes, definitely.", "You may rely on it.",
    "Most likely.", "Outlook good.", "Yes.", "Reply hazy, try again.",
    "Ask again later.", "Cannot predict now.", "Don't count on it.", "My reply is no.",
    "Outlook not so good.", "Very doubtful."
]

@tree.command(name="8ball", description="Ask the magic 8-ball a yes/no question!")
async def eight_ball(interaction: discord.Interaction, question: str):
    response = random.choice(EIGHT_BALL_RESPONSES)
    await interaction.response.send_message(f"🎱 {response}")

# /choose command - fixed to handle specific options
@tree.command(name="choose", description="Randomly choose between up to five options")
async def choose(interaction: discord.Interaction, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
    options = [option1, option2]

    if option3:
        options.append(option3)
    if option4:
        options.append(option4)
    if option5:
        options.append(option5)

    choice = random.choice(options)
    await interaction.response.send_message(f"🤔 I choose: **{choice}**!")

# Ship command
@tree.command(name="ship", description="Ship two random members together with a love score!")
async def ship(interaction: discord.Interaction):
    eligible_members = [
        member for member in interaction.guild.members
        if not member.bot and member.id not in EXCLUDED_USER_IDS and member.display_name not in EXCLUDED_USER_NAMES
    ]

    zeeke = discord.utils.get(interaction.guild.members, id=ZEKE_ID)
    allie = discord.utils.get(interaction.guild.members, id=ALLIE_ID)

    if zeeke and allie:
        eligible_members.extend([zeeke, allie] * 10)  # Add them 10 times to increase their chance

    if len(eligible_members) < 2:
        await interaction.response.send_message("Not enough eligible members to ship!", ephemeral=True)
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

    await interaction.response.send_message(
        f"{person1.mention} and {person2.mention} have a {compatibility_percentage}% compatibility! 💘\n{custom_message}"
    )

# Custom compatibility messages for /ship
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

# New command: ship_with_percentage
@tree.command(name="ship_with_percentage", description="Ship two users with a specified compatibility percentage.")
async def ship_with_percentage(interaction: discord.Interaction, person1: discord.Member, person2: discord.Member, percentage: int):
    if percentage < 0 or percentage > 100:
        await interaction.response.send_message("Please provide a percentage between 0 and 100.", ephemeral=True)
        return

    custom_message = get_custom_message(percentage)
    await interaction.response.send_message(
        f"{person1.mention} and {person2.mention} have a {percentage}% compatibility! 💘\n{custom_message}"
    )

# Sing a song by title
@tree.command(name="sing", description="The bot will sing a song by title.")
@has_restricted_roles()
async def sing(interaction: discord.Interaction, song_title: str):
    global is_singing
    song_title = song_title.lower()

    if song_title not in SONG_LYRICS:
        await interaction.response.send_message(
            f"Sorry, I don't know the song '{song_title}'. Available songs are: {', '.join(SONG_LYRICS.keys())}",
            ephemeral=True
        )
        return

    is_singing = True
    try:
        await interaction.response.send_message(f"🎤 Starting to sing '{song_title.title()}'! 🎶")

        for line in SONG_LYRICS[song_title]:
            if not is_singing:
                break
            await interaction.channel.send(line)
            await asyncio.sleep(2)

        if is_singing:
            await interaction.channel.send("🎤 Song finished! 🎶")
        else:
            await interaction.channel.send("🎤 Singing stopped. 🎶")

    except Exception as e:
        await interaction.channel.send("Oops! Something went wrong while singing.")
        logging.error(f"Error in /sing command: {e}")

# Stop singing command
@tree.command(name="stop_singing", description="Stops the bot from singing.")
@has_restricted_roles()
async def stop_singing(interaction: discord.Interaction):
    global is_singing
    is_singing = False
    await interaction.response.send_message("🎤 Stopping the song! 🎶")

# Send message command
if not tree.get_command('send_message'):
    @tree.command(name="send_message", description="Send a message to a specific channel.")
    @has_restricted_roles()
    async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, *, message: str):
        try:
            await channel.send(message)
            await interaction.response.send_message(f"Message sent to {channel.mention}", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in /send_message command: {e}")
            await interaction.response.send_message("An error occurred while sending the message.", ephemeral=True)

# Copy profile command
@tree.command(name="copy", description="Copy another user's profile.")
@has_restricted_roles()
async def copy(interaction: discord.Interaction, target: discord.Member):
    global original_bot_name, original_bot_avatar, original_bot_status, session

    if original_bot_name is None:
        original_bot_name = bot.user.name
    if original_bot_avatar is None:
        original_bot_avatar = await bot.user.avatar.read() if bot.user.avatar else None
    if original_bot_status is None:
        original_bot_status = bot.activity

    try:
        await bot.user.edit(username=target.display_name)
        if target.avatar:
            async with session.get(target.avatar.url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    await bot.user.edit(avatar=data)

        await bot.change_presence(activity=discord.Game(name=target.activity.name if target.activity else "No status"))
        await interaction.response.send_message(f"Copied {target.mention}'s profile successfully!")

    except Exception as e:
        logging.error(f"Error in /copy command: {e}")
        await interaction.response.send_message(f"Failed to copy {target.mention}'s profile.")

# Revert bot profile command
@tree.command(name="stop", description="Revert the bot back to its original profile.")
@has_restricted_roles()
async def stop(interaction: discord.Interaction):
    global original_bot_name, original_bot_avatar, original_bot_status

    try:
        if original_bot_name:
            await bot.user.edit(username=original_bot_name)
        if original_bot_avatar:
            await bot.user.edit(avatar=original_bot_avatar)
        if original_bot_status:
            await bot.change_presence(activity=original_bot_status)

        await interaction.response.send_message("Reverted back to the original profile!")
    except Exception as e:
        logging.error(f"Error in /stop command: {e}")
        await interaction.response.send_message("Failed to revert back to the original profile.")

# Marriage commands
@tree.command(name="marry", description="Marry two people.")
@has_restricted_roles()
async def marry(interaction: discord.Interaction, person1: discord.Member, person2: discord.Member):
    if (person1.id, person2.id) in marriages or (person2.id, person1.id) in marriages:
        await interaction.response.send_message(f"{person1.mention} and {person2.mention} are already married!")
        return

    marriages[(person1.id, person2.id)] = (person1.display_name, person2.display_name)
    save_marriages()
    await interaction.response.send_message(f"🎉 {person1.mention} and {person2.mention} just got married! 💍")

@tree.command(name="remove_marriage", description="Remove a marriage.")
@has_restricted_roles()
async def remove_marriage(interaction: discord.Interaction, person1: discord.Member, person2: discord.Member):
    if (person1.id, person2.id) in marriages:
        del marriages[(person1.id, person2.id)]
    elif (person2.id, person1.id) in marriages:
        del marriages[(person2.id, person1.id)]
    else:
        await interaction.response.send_message(f"{person1.mention} and {person2.mention} are not married!")
        return

    save_marriages()
    await interaction.response.send_message(f"💔 {person1.mention} and {person2.mention} are no longer married.")

# Save marriages to a file
def save_marriages():
    try:
        with open(MARRIAGES_FILE, 'w') as f:
            json.dump(marriages, f, indent=4)
            logging.info("Marriages saved to file.")
    except Exception as e:
        logging.error(f"Error saving marriages: {e}")

# Load marriages from a file
def load_marriages():
    global marriages
    try:
        with open(MARRIAGES_FILE, 'r') as f:
            marriages = json.load(f)
            logging.info("Marriages loaded from file.")
    except FileNotFoundError:
        logging.info("No marriages file found. Starting fresh.")
    except Exception as e:
        logging.error(f"Error loading marriages: {e}")

# Message delete detection (ignores messages deleted by any bot or webhooks)
@bot.event
async def on_message_delete(message):
    # Check if the message was sent by a bot or webhook
    if message.author.bot or message.webhook_id is not None:
        return  # Ignore messages deleted by bots or webhooks

    # Only proceed if the message was deleted in a guild (server)
    if message.guild and message.content:
        try:
            # Check if the deleted message was a reply to someone
            if message.reference and message.reference.resolved:
                replied_user = message.reference.resolved.author
                reply_info = f"(This was a reply to {replied_user.mention})"
            else:
                reply_info = ""

            # Send an embed with information about the deleted message
            embed = discord.Embed(
                description=f"{message.author.mention} just deleted a message: '{message.content}' {reply_info} in {message.channel.mention}",
                color=discord.Color.red()
            )

            await message.channel.send(embed=embed)

        except discord.Forbidden:
            logging.error("Bot does not have permission to send messages in this channel.")
        except Exception as e:
            logging.error(f"Error sending deleted message log: {e}")

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
    load_marriages()
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
