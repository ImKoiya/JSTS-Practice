import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from datetime import datetime

milky_way = discord.Object(id=1000861726759190528)
development_server = discord.Object(id=1312229548091379774)
server = milky_way

@app_commands.guilds(server)
class member(commands.GroupCog, group_name='member'):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="info", description="Gets a members info.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member you want to receive the info for")
    async def info(self, interaction: discord.Interaction, member: discord.Member):
        member_info_embed = discord.Embed(title="", description="avatar", url=member.avatar.url)
        member_info_embed.set_author(name=member.display_name, icon_url=member.avatar)
        role_string = ""

        for role in member.roles:
            if role.name == "@everyone":
                continue
            else:
                role_string += f"{role.mention} "
        
        member_info_embed.add_field(name="**Roles**", value=role_string)
        member_info_embed.add_field(name="**Created**", value=f"<t:{int(member.created_at.timestamp())}:R>")
        member_info_embed.add_field(name="**Joined**", value=f"<t:{int(member.joined_at.timestamp())}:R>")
        member_info_embed.set_footer(text=f"ID: {member.id}")

        await interaction.response.send_message(embed=member_info_embed)

    @app_commands.command(name="avatar", description="Get a full size version of a members avatar")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to get the avatar for")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member):
        avatar_embed = discord.Embed(title=f"Avatar for {member.display_name}")
        avatar_embed.set_author(name=f"Command ran by {interaction.user.display_name}", icon_url=interaction.user.display_avatar)
        avatar_embed.set_footer(text=f"ID: {member.id}")
        avatar_embed.set_image(url=member.display_avatar)

        await interaction.response.send_message(embed=avatar_embed)

async def setup(client: commands.Bot):
    await client.add_cog(member(client))