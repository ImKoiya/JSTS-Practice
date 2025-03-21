import discord
from discord.ext import commands
from discord import Embed
from discord import app_commands
import json
import asyncio
from collections import defaultdict


BOT_TOKEN = ''
#Izanami

allowed_user_id = 239870595976658945
rate_limit_tracker = defaultdict(float)
RATE_LIMIT_COOLDOWN = 5

user_emotes_mapping = {}
# Load user emote mapping data from the JSON file and store it in the in-memory cache
def load_user_emotes():
    global user_emotes_mapping
    try:
        with open('user_emotes.json', 'r') as file:
            user_emotes_mapping = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        user_emotes_mapping = {}

# Save user emote mapping data to the JSON file
def save_user_emotes(data):
    try:
        with open('user_emotes.json', 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Error saving user emotes to JSON: {e}")

load_user_emotes()  # Load user emotes when bot starts

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='i!', intents=intents)
client = discord.Client(intents=intents)

def has_admin_permissions_or_owner(interaction: discord.Interaction):
    return interaction.user.id == bot.owner_id or interaction.user.guild_permissions.administrator

def get_user_emotes(user_id):
    return user_emotes_mapping.get(str(user_id), {})

def update_user_emotes(user_id, emotes):
    user_emotes_mapping[str(user_id)] = emotes
    save_user_emotes(user_emotes_mapping)


# Create a cache dictionary to store fetched messages
message_cache = {}
CACHE_MAX_SIZE = 100  # Maximum number of messages to keep in the cache
CACHE_EXPIRY_TIME = 60 * 5  # Cache expiry time in seconds (e.g., 5 minutes)


async def is_reply_to_specific_person(message, user_id):
    if not message.reference or not message.reference.message_id:
        return False

    # Check if the message is already in the cache and not expired
    if message.reference.message_id in message_cache:
        replied_message, timestamp = message_cache[message.reference.message_id]
        current_time = asyncio.get_event_loop().time()
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            return replied_message.author.id == int(user_id)

    # If not in cache or expired, fetch the message
    try:
        replied_message = await message.channel.fetch_message(message.reference.message_id)
        # Add the fetched message to the cache with a timestamp
        message_cache[message.reference.message_id] = (replied_message, asyncio.get_event_loop().time())

        # Clean up the cache if it exceeds the maximum size
        if len(message_cache) > CACHE_MAX_SIZE:
            # Get the oldest message based on timestamp
            oldest_message_id = min(message_cache, key=lambda k: message_cache[k][1])
            del message_cache[oldest_message_id]
    except discord.NotFound:
        return False  # Message not found, return False

    return replied_message.author.id == int(user_id)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    try:
        with open('presence.json', 'r') as f:
            data = json.load(f)
            activity_type = data.get('activity_type', 'playing')
            status = data.get('status', 'Hello, World!')
            await set_bot_presence(activity_type, status)
    except FileNotFoundError:
        print("No saved presence data found. Using default presence.")
    synced = await bot.tree.sync()
    bot.owner_id = (await bot.application_info()).owner.id


@bot.tree.command(name="set_presence", description="Set the bot's presence")
async def set_presence(interaction: discord.Interaction, presence_type: str, status: str):
    # Manually check if the user is the bot owner
    if interaction.user.id != bot.owner_id:
        await interaction.response.send_message("You do not have permission to change the bot's presence.", ephemeral=True)
        return

    try:
        await set_bot_presence(presence_type, status)

        # Save the presence data to a JSON file
        presence_data = {'activity_type': presence_type, 'status': status}
        with open('presence.json', 'w') as f:
            json.dump(presence_data, f)

        # Create an embedded message to indicate the presence change
        embed = discord.Embed(title="Bot Presence Updated", color=0xb77cf3)
        embed.add_field(name="Presence Type", value=presence_type.capitalize(), inline=False)
        embed.add_field(name="Status", value=status, inline=False)

        # Send the embedded message in chat
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def set_bot_presence(presence_type, status):
    if presence_type.lower() == 'playing':
        activity = discord.Game(name=status)
    elif presence_type.lower() == 'streaming':
        activity = discord.Streaming(name=status, url='https://www.twitch.tv/velkyen')
    elif presence_type.lower() == 'listening':
        activity = discord.Activity(type=discord.ActivityType.listening, name=status)
    elif presence_type.lower() == 'watching':
        activity = discord.Activity(type=discord.ActivityType.watching, name=status)
    else:
        raise commands.BadArgument('Invalid presence type. Available types: playing, streaming, listening, watching')

    await bot.change_presence(activity=activity)
    print(f'Presence changed to: {presence_type} {status}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    mentioned_user_ids = [str(mention.id) for mention in message.mentions]

    for user_id in user_emotes_mapping:  # Iterating through user_emotes_mapping keys
        emote_names = get_user_emotes(user_id)  # Retrieve emote names for the specific user_id
        if user_id in mentioned_user_ids or await is_reply_to_specific_person(message, user_id):
            for emote_name in emote_names:
                emote = discord.utils.get(bot.emojis, name=emote_name)
                if emote:
                    try:
                        await message.add_reaction(emote)
                        await asyncio.sleep(0.1)
                    except discord.errors.HTTPException as e:
                        if e.status == 429:
                            print("Rate limited. Sleeping for a while.")
                            await asyncio.sleep(5)
                        else:
                            print(f"Other HTTP Exception: {e}")
                else:
                    print(f"Emote '{emote_name}' not found in the server's emoji list.")


    return False


@bot.tree.command(name="add_emote", description="Add an emote for a user")
@app_commands.check(has_admin_permissions_or_owner)
async def add_emote(interaction: discord.Interaction, target: discord.User, emote: str):
    if not (emote.startswith('<') and emote.endswith('>')):
        await interaction.response.send_message("Invalid emote format. Please use the format <:emote_name:emote_id> or <a:emote_name:emote_id>.", ephemeral=True)
        return

    emote_parts = emote.split(':')
    emote_name = emote_parts[1]
    emote_id = emote_parts[2].replace('>', '')

    user_id = str(target.id)
    if user_id not in user_emotes_mapping:
        user_emotes_mapping[user_id] = {}

    user_emotes_mapping[user_id][emote_name] = int(emote_id) if emote_id else None

    update_user_emotes(target.id, user_emotes_mapping.get(str(target.id), {}))

    embed = Embed(
        title="Emote Added",
        description=f"Added emote :{emote_name}: for {target.mention}.",
        color=0xb77cf3
    )
    await interaction.response.send_message(embed=embed)
    #print(f"User emotes data saved: {user_emotes_mapping}")


@bot.tree.command(name="remove_emote", description="Remove an emote from a user")
@app_commands.check(has_admin_permissions_or_owner)
async def remove_emote(interaction: discord.Interaction, target: discord.User, emote_name: str):
    user_id = str(target.id)
    if user_id in user_emotes_mapping and emote_name in user_emotes_mapping[user_id]:
        del user_emotes_mapping[user_id][emote_name]
        update_user_emotes(target.id, user_emotes_mapping.get(str(target.id), {}))

        embed = Embed(
            title="Emote Removed",
            description=f"Emote :{emote_name}: removed for {target.mention}.",
            color=0xb77cf3
        )
        await interaction.response.send_message(embed=embed)
        print(f"User emotes data saved: {user_emotes_mapping}")
    else:
        embed = Embed(
            title="Emote Not Found",
            description=f"No emote found with the name :{emote_name}: for {target.mention}.",
            color=0xb77cf3
        )
        await interaction.response.send_message(embed=embed)


@add_emote.error
@remove_emote.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You need to have administrator permissions to use this command.", ephemeral=True)
    elif "The application did not respond" in str(error):
        await ctx.send("The application did not respond.", ephemeral=True)


bot.run(BOT_TOKEN)
