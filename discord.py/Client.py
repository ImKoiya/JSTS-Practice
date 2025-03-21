import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
flaire_token = os.getenv("flaire-token")
testing_token = os.getenv("test-token")
developing = True
milky_way = discord.Object(id=1000861726759190528)
development_server = discord.Object(id=1312229548091379774)
server = milky_way
token = str(flaire_token)
cogs = []

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True
intents.guilds = True

client = commands.Bot(command_prefix="F-", intents=intents)
client.remove_command('help')

async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith(".py"):
            cogs.append(f"cogs.{filename[:-3]}")

    if __name__ == '__main__':
        for extension in cogs:
            await client.load_extension(extension)
        print("All cogs have been loaded.")

@client.event
async def on_ready():
    try:
        await client.tree.sync(guild=server)
    except Exception as e:
        print(e)
    print(f'We have logged in as {client.user.name}')

    try:
        with open('presence.json', 'r') as f:
            data = json.load(f)
        activity_type = data.get('activity_type', 'playing')
        status = data.get('status', 'Hello, World!')
        await set_bot_presence(activity_type, status)
    except FileNotFoundError:
        print("No saved presence data found. Using default presence.")

async def main():
    os.system('clear')
    await load()
    await client.start(token=token)

@client.tree.command(name="ping", description="Returns the bots ping.", guild=server)
@app_commands.checks.has_permissions(manage_channels=True)
async def ping(interaction: discord.Interaction):
    ping_embed = discord.Embed(title="Pong!", description=f"{round(client.latency * 1000)}ms")
    ping_embed.set_author(name=client.user.name, icon_url=client.user.avatar)
    ping_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
    return await interaction.response.send_message(embed=ping_embed)

@client.tree.command(name="set_presence", description="Set the bot's presence", guild=server)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(presence_type=[app_commands.Choice(name="playing", value="playing"),
                                     app_commands.Choice(name="streaming", value="streaming"),
                                     app_commands.Choice(name="listening", value="listening"),
                                     app_commands.Choice(name="watching", value="watching")])
async def set_presence(interaction: discord.Interaction, presence_type: app_commands.Choice[str], status: str):
    try:
        await set_bot_presence(presence_type.value, status)

        # Save the presence data to a JSON file
        presence_data = {'activity_type': presence_type.value, 'status': status}
        with open('presence.json', 'w') as f:
            json.dump(presence_data, f)

        # Create an embedded message to indicate the presence change
        embed = discord.Embed(title="Bot Presence Updated", color=0xb77cf3)
        embed.add_field(name="Presence Type", value=presence_type.value.capitalize(), inline=False)
        embed.add_field(name="Status", value=status, inline=False)
#Send the embedded message in chat
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

    await client.change_presence(activity=activity)  # Use client instead of bot
    print(f'Presence changed to: {presence_type} {status}')

@client.tree.command(name="purge", description="Purge the entered amount of messages. (standard 100)", guild=server)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Amount of messages to purge.", member="The specific member to purge the messages of.")
@app_commands.checks.cooldown(1, 5)
async def purge(interaction: discord.Interaction, amount: int=100, member: discord.Member=None):
    
    
    if member:
        await interaction.response.send_message(f"Purging {interaction.channel.mention} of messages sent by {member.display_name}")
        await asyncio.sleep(1.25)
        await interaction.channel.purge(limit=amount, check=lambda message: message.author == member)
    else:
        await interaction.response.send_message(f"Purging {interaction.channel.mention} of {amount} messages")
        await asyncio.sleep(1.25)
        await interaction.channel.purge(limit=amount)

    await asyncio.sleep(0.75)
    purge_embed = discord.Embed(title=f"{amount} messages purged")
    purge_embed.set_author(name=f"Ran by {interaction.user.display_name}", icon_url=interaction.user.display_avatar)
    purge_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
    await interaction.channel.send(embed=purge_embed)

asyncio.run(main())