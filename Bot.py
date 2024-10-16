import os
import discord
import random
import logging
import aiohttp
import json
import asyncio
from discord import app_commands
from discord.ext import commands
from collections import defaultdict  # For cat-catching game

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
        "But I can't ignore the crazy visions of me in LA",
        "I'm taking time to do what's right for me",
        "Taking time for everyone I see",
        "Oh, I'm going to the pony club",
        "Just to prove that I'm on top",
        "Oh, I'm going to the pony club",
        "Just to show that I'm in luck",
        "I'm no longer a fool",
        "I'm just riding for the thrill",
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
        "(If you get off me)",
        "I love a little drama, let's start a bar fight",
        "(Then we can kick 'em all out)",
        "'Cause everything good happens",
        "After midnight",
        "I'm feeling kinda freaky, maybe it's the moonlight (ah)",
        "I kinda wanna kiss your boyfriend if you don't mind",
        "(If you don't, if you don't mind)",
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

# Cat catching game setup
cat_catches = defaultdict(int)  # Tracks how many cats each user has caught
cat_spawned = False  # Flag to check if a cat is currently available
cat_channel = None  # The channel where the cat spawns
cat_catcher = None  # The user who caught the cat

# Restrict command access to specific roles
def has_restricted_roles():
    async def predicate(interaction: discord.Interaction):
        allowed_roles = ALLOWED_ROLE_IDS  # List of allowed role IDs
        user_roles = [role.id for role in interaction.user.roles]

        if any(role_id in user_roles for role_id in allowed_roles):
            return True

        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Function to spawn a cat
async def spawn_cat():
    global cat_spawned, cat_channel
    await asyncio.sleep(random.randint(60, 300))  # Random spawn time between 1 and 5 minutes

    # Ensure a channel is set for cat spawning
    if not cat_channel:
        print("No channel set for cat spawning.")
        return

    await cat_channel.send("A wild 🐱 **cat** has appeared! Type `cat` to catch it!")
    cat_spawned = True  # Set the flag to indicate a cat is spawned

# Listen for messages to catch the cat
@bot.event
async def on_message(message):
    global cat_spawned, cat_catcher

    # Check if the message is in the right channel and the cat is spawned
    if cat_spawned and message.channel == cat_channel and message.content.lower() == "cat":
        cat_spawned = False  # Reset the spawn flag
        cat_catcher = message.author
        cat_catches[cat_catcher.id] += 1  # Increment catch count for the user

        await message.channel.send(f"🎉 {message.author.mention} caught the cat! They've now caught {cat_catches[cat_catcher.id]} cat(s).")

        # Optionally, start the next cat spawn
        await asyncio.create_task(spawn_cat())  # Start another spawn

    await bot.process_commands(message)

# Command to set the channel for cat spawning
@tree.command(name="set_cat_channel", description="Set the channel where cats will spawn.")
@has_restricted_roles()
async def set_cat_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global cat_channel
    cat_channel = channel
    await interaction.response.send_message(f"Cats will now spawn in {channel.mention}.")
    await asyncio.create_task(spawn_cat())  # Start the first spawn

# Command to display the leaderboard
@tree.command(name="cat_leaderboard", description="Check the top cat catchers.")
async def cat_leaderboard(interaction: discord.Interaction):
    if not cat_catches:
        await interaction.response.send_message("No one has caught a cat yet! 😿")
        return

    leaderboard = sorted(cat_catches.items(), key=lambda x: x[1], reverse=True)
    leaderboard_message = "**Cat Catch Leaderboard**:\n"
    for i, (user_id, catch_count) in enumerate(leaderboard[:10], start=1):
        user = await bot.fetch_user(user_id)
        leaderboard_message += f"{i}. {user.name} - {catch_count} cats\n"

    await interaction.response.send_message(leaderboard_message)

# Command to reset the leaderboard
@tree.command(name="reset_cat_leaderboard", description="Reset the cat catching leaderboard.")
@has_restricted_roles()
async def reset_cat_leaderboard(interaction: discord.Interaction):
    global cat_catches
    cat_catches.clear()  # Reset the leaderboard
    await interaction.response.send_message("Cat catching leaderboard has been reset.")

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

# Bot setup hook
async def setup_hook():
    global session
    session = aiohttp.ClientSession()
    logging.info("Bot setup complete.")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

# Run the bot using the token from the environment variable
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logging.error(f"Error starting the bot: {e}")
