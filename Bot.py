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

# Role IDs for restricted commands
ALLOWED_ROLE_IDS = [1292555279246032916, 1292555408724066364]

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

# Global flag to control the singing process
is_singing = False

# Dictionary to store multiple songs with titles as keys
SONG_LYRICS = {
    "pony club": [
        "I know you wanted me to stay",
        "But I can't ignore the crazy visions of me in LA",
        "And I heard that there's a special place",
        "Where boys and girls can all be queens every single day",
        "I'm having wicked dreams of leaving Tennessee",
        "Hear Santa Monica, I swear it's calling me",
        "Won't make my mama proud, it's gonna cause a scene",
        "She sees her baby girl, I know she's gonna scream",
        "God, what have you done?",
        "You're a pink pony girl",
        "And you dance at the club",
        "Oh mama, I'm just having fun",
        "On the stage in my heels",
        "It's where I belong down at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing down in",
        "West Hollywood",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club, Pink Pony Club",
        "I'm up and jaws are on the floor",
        "Lovers in the bathroom and a line outside the door",
        "Blacklights and a mirrored disco ball",
        "Every night's another reason why I left it all",
        "I thank my wicked dreams a year from Tennessee",
        "Oh, Santa Monica, you've been too good to me",
        "Won't make my mama proud, it's gonna cause a scene",
        "She sees her baby girl, I know she's gonna scream",
        "God, what have you done?",
        "You're a pink pony girl",
        "And you dance at the club",
        "Oh mama, I'm just having fun",
        "On the stage in my heels",
        "It's where I belong down at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing down in",
        "West Hollywood",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club, Pink Pony Club",
        "Don't think I've left you all behind",
        "Still love you and Tennessee",
        "You're always on my mind",
        "And mama, every Saturday",
        "I can hear your southern drawl a thousand miles away, saying",
        "God, what have you done?",
        "You're a pink pony girl",
        "And you dance at the club",
        "Oh mama, I'm just having fun",
        "On the stage in my heels",
        "It's where I belong down at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club",
        "I'm gonna keep on dancing down in",
        "West Hollywood",
        "I'm gonna keep on dancing at the",
        "Pink Pony Club, Pink Pony Club",
        "I'm gonna keep on dancing",
        "I'm gonna keep on dancing"
    ],
    "after midnight": [
        "My mama said, 'Nothing good happens",
        "When it's late and you're dancing alone'",
        "She's in my head saying, 'It's not attractive",
        "Wearing that dress and red lipstick'",
        "This is what I wanted, this is what I like",
        "I've been a good, good girl for a long time (this is what I like)",
        "But, baby, I like flirting, a lover by my side",
        "Can't be a good, good girl, even if I tried",
        "'Cause after midnight",
        "I'm feeling kinda freaky, maybe it's the club lights",
        "I kinda wanna kiss your girlfriend if you don't mind",
        "I love a little drama, let's start a bar fight",
        "'Cause everything good happens",
        "After midnight",
        "I'm feeling kinda freaky, maybe it's the moonlight",
        "I kinda wanna kiss your boyfriend if you don't mind",
        "I love a little, uh-huh, let's watch the sunrise",
        "'Cause everything good happens after",
        "I really want your hands on my body",
        "A slow dance, baby, let's get it on",
        "That's my type of fun, that's my kind of party",
        "Your hands on my body, your hot hands",
        "This is what I wanted, this is what I like",
        "I've been a good, good girl for a long time (it's what I wanted)",
        "Baby, I like flirting, a lover by my side",
        "Can't be a good, good girl, even if I tried",
        "'Cause after midnight",
        "I'm feeling kinda freaky, maybe it's the club lights",
        "I kinda wanna kiss your girlfriend if you don't mind",
        "I love a little drama, let's start a bar fight",
        "'Cause everything good happens",
        "After midnight",
        "I'm feeling kinda freaky, maybe it's the moonlight",
        "I kinda wanna kiss your boyfriend if you don't mind",
        "I love a little uh-huh, let's watch the sunrise",
        "'Cause everything good happens after midnight",
        "Baby, put your hands up, be a freak in the club",
        "Yeah, we'll make a move, then we're making out",
        "Yeah, we're makin', make love (it's what I want)",
        "Yeah, we're makin', make love, be a freak in the club",
        "Be a freak in the club, yeah",
        "'Cause after midnight",
        "I'm feeling kinda freaky, maybe it's the club lights",
        "I kinda wanna kiss your girlfriend if you don't mind",
        "(If you get off me)",
        "I love a little drama, let's start a bar fight",
        "(Then we can kick 'em all out)",
        "'Cause everything good happens",
        "After midnight",
        "I'm feeling kinda freaky, maybe it's the moonlight (ah)",
        "I kinda wanna kiss your boyfriend if you don't mind",
        "(If you don't, if you don't mind)",
        "I love a little uh-huh, let's watch the sunrise",
        "'Cause everything good happens after-"
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
    async def predicate(ctx):
        allowed_roles = ALLOWED_ROLE_IDS  # List of allowed role IDs
        user_roles = [role.id for role in ctx.author.roles]

        if any(role_id in user_roles for role_id in allowed_roles):
            return True

        # Send an error message if the user doesn't have the required role
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return False
    return commands.check(predicate)

# Ship command
@bot.command(name="ship", help="Ship two random members together with a love score!")
@commands.cooldown(1, 60, commands.BucketType.user)  # 1 minute cooldown
async def ship(ctx):
    eligible_members = [
        member for member in ctx.guild.members 
        if not member.bot and member.id not in EXCLUDED_USER_IDS and member.display_name not in EXCLUDED_USER_NAMES
    ]

    zeeke = discord.utils.get(ctx.guild.members, id=ZEKE_ID)
    allie = discord.utils.get(ctx.guild.members, id=ALLIE_ID)

    if zeeke and allie:
        eligible_members.extend([zeeke, allie] * 10)  # Add them 10 times to increase their chance

    if len(eligible_members) < 2:
        await ctx.send("Not enough eligible members to ship!")
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

    await ctx.send(
        f"{person1.mention} and {person2.mention} have a {compatibility_percentage}% compatibility! 💘\n{custom_message}"
    )

# Custom compatibility messages
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

# Sing a song by title
@bot.command(name="sing", help="The bot will sing a song by title (e.g., !sing pony club or !sing after midnight).")
@has_restricted_roles()  # Restrict to specific roles
async def sing(ctx, *, song_title: str):
    global is_singing
    song_title = song_title.lower()

    # Check if the requested song is in the SONG_LYRICS dictionary
    if song_title not in SONG_LYRICS:
        await ctx.send(f"Sorry, I don't know the song '{song_title}'. Available songs are: {', '.join(SONG_LYRICS.keys())}")
        return

    is_singing = True  # Set the flag to True to indicate singing has started
    try:
        await ctx.send(f"🎤 Starting to sing '{song_title.title()}'! 🎶")

        for line in SONG_LYRICS[song_title]:
            if not is_singing:  # Stop singing if the stop command is used
                break
            await ctx.send(line)
            await asyncio.sleep(2)  # Wait for 2 seconds between each line

        if is_singing:
            await ctx.send("🎤 Song finished! 🎶")
        else:
            await ctx.send("🎤 Singing stopped. 🎶")

    except Exception as e:
        await ctx.send("Oops! Something went wrong while singing.")
        logging.error(f"Error in /sing command: {e}")

# Stop singing command
@bot.command(name="stop_singing", help="Stops the bot from singing.")
@has_restricted_roles()  # Restrict to specific roles
async def stop_singing(ctx):
    global is_singing
    is_singing = False  # Set the flag to False to stop the bot from singing
    await ctx.send("🎤 Stopping the song! 🎶")

# Marriage commands
@bot.command(name="marry", help="Marry two people.")
@has_restricted_roles()  # Restrict to specific roles
async def marry(ctx, person1: discord.Member, person2: discord.Member):
    # Ensure they are not already married
    if (person1.id, person2.id) in marriages or (person2.id, person1.id) in marriages:
        await ctx.send(f"{person1.mention} and {person2.mention} are already married!")
        return

    marriages[(person1.id, person2.id)] = (person1.display_name, person2.display_name)
    save_marriages()  # Save marriages after adding
    await ctx.send(f"🎉 {person1.mention} and {person2.mention} just got married! 💍")

@bot.command(name="remove_marriage", help="Remove a marriage.")
@has_restricted_roles()  # Restrict to specific roles
async def remove_marriage(ctx, person1: discord.Member, person2: discord.Member):
    # Check if the two people are married
    if (person1.id, person2.id) in marriages:
        del marriages[(person1.id, person2.id)]
    elif (person2.id, person1.id) in marriages:
        del marriages[(person2.id, person1.id)]
    else:
        await ctx.send(f"{person1.mention} and {person2.mention} are not married!")
        return

    save_marriages()  # Save marriages after removal
    await ctx.send(f"💔 {person1.mention} and {person2.mention} are no longer married.")

@bot.command(name="check_marriages", help="Check all current marriages.")
async def check_marriages(ctx):
    if not marriages:
        await ctx.send("There are no current marriages.")
        return
    marriage_list = "\n".join([f"{p1} ❤ {p2}" for (_, (p1, p2)) in marriages.items()])
    await ctx.send(f"Here are the current marriages:\n\n{marriage_list}")

# Copy profile command
@bot.command(name="copy", help="Copy another user's profile.")
@has_restricted_roles()  # Restrict to specific roles
async def copy(ctx, target: discord.Member):
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
        await ctx.send(f"Copied {target.mention}'s profile successfully!")

    except Exception as e:
        logging.error(f"Error in /copy command: {e}")
        await ctx.send(f"Failed to copy {target.mention}'s profile.")

# Revert bot profile command
@bot.command(name="stop", help="Revert the bot back to its original profile.")
@has_restricted_roles()  # Restrict to specific roles
async def stop(ctx):
    global original_bot_name, original_bot_avatar, original_bot_status

    try:
        if original_bot_name:
            await bot.user.edit(username=original_bot_name)
        if original_bot_avatar:
            await bot.user.edit(avatar=original_bot_avatar)
        if original_bot_status:
            await bot.change_presence(activity=original_bot_status)

        await ctx.send("Reverted back to the original profile!")
    except Exception as e:
        logging.error(f"Error in /stop command: {e}")
        await ctx.send("Failed to revert back to the original profile.")

# Send message command
@bot.command(name="send_message", help="Send a message to a specific channel.")
@has_restricted_roles()  # Restrict to specific roles
async def send_message(ctx, channel: discord.TextChannel, *, message: str):
    try:
        await channel.send(message)
        await ctx.send(f"Message sent to {channel.mention}")
    except Exception as e:
        logging.error(f"Error in /send_message command: {e}")
        await ctx.send("An error occurred while sending the message.")

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

# Bot setup hook
async def setup_hook():
    try:
        load_marriages()  # Load marriages when bot starts
        logging.info("Successfully initialized bot.")
    except Exception as e:
        logging.error(f"Error setting up bot: {e}")

bot.setup_hook = setup_hook

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
    
