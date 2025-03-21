import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from datetime import timedelta
from .utilities.Pagination import Pagination
import sqlite3
from cogs.log import log

server = discord.Object(1352389107778846831)
con = sqlite3.connect("moderation.db")
cur = con.cursor()
global modlog_channel_name
modlog_channel_name = log.get_channel(log, "modlog_channel", server.id)

@app_commands.guilds(server)
class moderation(commands.GroupCog, group_name='moderation'):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="kick", description="Kicks a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick.",
                           reason="The reason why this memer is being kicked (optional)")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str="No reason provided.") -> None:
        await member.kick(reason=reason)
        kick_embed = discord.Embed(title=f"{member.display_name} has been kicked.")
        kick_embed.set_author(name=f"Kicked by {interaction.user.display_name}", icon_url=interaction.user.avatar)
        kick_embed.set_thumbnail(url=member.avatar)
        kick_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
        kick_embed.description = f"Reason:\n{reason}"

        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])
        
        await modlog_channel.send(embed=kick_embed)
        await interaction.response.send_message(embed=kick_embed)

    #Implementing the ban command.
    #Checks if the user issuing the command has the correct permissions.
    @app_commands.command(name="ban", description="Bans a user from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="The user to ban.",
                           delete_messages="if you want to delete the members messages upon ban, (True by default).",
                           soft_ban="whether it's a soft ban or not.",
                           reason="The reason why this member is being banned (optional).")
    async def ban(self, interaction: discord.Interaction, user: discord.User, delete_messages: bool=True, soft_ban: bool=None, reason: str="No reason provided"):
        await interaction.response.defer()
        #Creating an embed to reply to the interaction with.
        ban_embed = discord.Embed(title=f"{user.display_name} has been banned.")
        ban_embed.set_author(name=f"Banned by {interaction.user.display_name}", icon_url=interaction.user.avatar)
        ban_embed.set_thumbnail(url=user.avatar)
        ban_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))

        ban_embed.description = f"Reason:\n{reason}"

        #Actually bans the member (finally lol).
        await interaction.guild.ban(user, delete_message_days=int(delete_messages), reason=reason)
        #Checks if it was a soft-ban, instantly unbans the user if that's the case, also updates the embed title accordingly.
        if soft_ban:
            ban_embed.title = f"{user.display_name} has been soft-banned."
            await interaction.guild.unban(discord.Object(id=user.id))

        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])
        
        #Sends the embed as response to the interaction.
        await modlog_channel.send(embed=ban_embed)
        await interaction.followup.send(embed=ban_embed)
    
    @app_commands.command(name="unban", description="Unbans the given user.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user='The user to unban', reason='The reason this user is being unbanned (optional)')
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str="No reason provided."):
        unban_embed = discord.Embed(title=f"{user.display_name} has been unbanned.")
        unban_embed.set_author(name=f"Unbanned by {interaction.user.display_name}", icon_url=interaction.user.avatar)
        unban_embed.description = reason
        unban_embed.set_thumbnail(url=user.avatar)
        unban_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
        
        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])

        await interaction.guild.unban(user=user, reason=reason)
        await modlog_channel.send(embed=unban_embed)
        await interaction.response.send_message(embed=unban_embed)
    
    @app_commands.command(name="timeout", description="Add or remove a timeout.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to timeout", duration="The time to timeout someone for", options="choice to minute some for the given amount of minutes, hours, days or weeks", reason="Reason for the timeout")
    @app_commands.choices(options=[app_commands.Choice(name="Minute(s)", value="minute"), app_commands.Choice(name="Hour(s)", value="hour"), app_commands.Choice(name="Day(s)", value="day"), app_commands.Choice(name="Week(s)", value="week"), app_commands.Choice(name="Remove", value="remove")])
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, options: app_commands.Choice[str]=None, duration: int=1, reason: str = "No reason provided"):
        await interaction.response.defer()
        timeout_duration = timedelta()

        match options:
            case app_commands.Choice(name="Minute(s)", value="minute"):
                if duration > 40320:
                    duration = 40320
                timeout_duration += timedelta(minutes=duration)
            case app_commands.Choice(name="Hour(s)", value="hour"):
                if duration > 672:
                    duration = 672
                timeout_duration += timedelta(hours=duration)
            case app_commands.Choice(name="Day(s)", value="day"):
                if duration > 28:
                    duration = 28
                timeout_duration += timedelta(days=duration)
            case app_commands.Choice(name="Week(s)", value="week"):
                if duration > 4:
                    duration = 4
                timeout_duration += timedelta(weeks=duration)
            case app_commands.Choice(name="Remove", value="remove"):
                await member.edit(timed_out_until=None)
            case _:
                timeout_duration += timedelta(hours=duration)

        # Create reply embed
        timeout_embed = discord.Embed()
        timeout_embed.description = reason
        timeout_embed.set_author(name=f"Timed out by {interaction.user.display_name}", icon_url=interaction.user.avatar)
        timeout_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))

        # Apply timeout
        if (timeout_duration.total_seconds() == 0):
            pass
        else:
            await member.timeout(timeout_duration, reason=reason)

        if (duration == 1 and options is None):
            timeout_embed.title = f"{member.display_name} has been timed out for 1 hour."
        elif (options.value == "remove"):
            timeout_embed.title = f"{member.display_name} had their timeout removed."
        elif (duration == 1):
            timeout_embed.title = f"{member.display_name} has been timed out for {duration} {options.value}."
        else:
            timeout_embed.title = f"{member.display_name} has been timed out for {duration} {options.value}s."

        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])   

        await modlog_channel.send(embed=timeout_embed)
        await interaction.followup.send(embed=timeout_embed)

    @app_commands.command(name="warn", description="Give someone a warning.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to give the warning to.",
                           warning="The warning you're giving the member.")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, warning: str):
        try:
            warn_time = int(datetime.now().timestamp())
            cur.execute("INSERT INTO warnings (user, reason, time, guild) VALUES (?, ?, ?, ?)", (member.id, warning, warn_time, interaction.guild.id))
            con.commit()
            dm_channel = await member.create_dm()

            cur.execute("SELECT id FROM warnings where user = (?) AND reason = (?) AND time = (?) AND guild = (?)", (member.id, warning, warn_time, interaction.guild.id))
            id = cur.fetchone()

            warn_embed = discord.Embed(title=f"{member.display_name} has been warned.")
            dm_embed = discord.Embed(title=f"You've been warned.")
            warn_embed.set_author(name=f"Warned by {interaction.user.display_name}", icon_url=interaction.user.avatar)
            dm_embed.set_author(name=f"You've been warned in {interaction.guild.name}", icon_url=interaction.guild.icon)
            warn_embed.description = f"Warn ID: {id[0]}\n{warning}"
            dm_embed.description = f"Warn ID: {id[0]}\n{warning}"
            warn_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
            dm_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))

            modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])

            await dm_channel.send(embed=dm_embed)
            await modlog_channel.send(embed=warn_embed)
            await interaction.response.send_message(embed=warn_embed)
        except Exception as e:
            if isinstance(e, app_commands.CommandInvokeError):
                await interaction.response.send_message("Failed to DM the user you were trying to reach.", embed=warn_embed)
            elif isinstance(e, app_commands.MissingPermissions):
                await interaction.response.send_message("You're missing permissions to run this command!", ephemeral=True)
            elif isinstance(e, discord.Forbidden):
                await interaction.response.send_message("Failed to DM the user you were trying to reach.", embed=warn_embed)

    @app_commands.command(name="remove_warn", description="Remove a warning from the logs based on the warning-ID")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(warn_id="The ID of the warning you're trying to delete.")
    async def RemoveWarn(self, interaction: discord.Interaction, warn_id: int):
        cur.execute("SELECT user, reason from warnings WHERE id = (?) AND guild = (?)", (warn_id, interaction.guild.id))
        Warning_deleted = cur.fetchone()
        warned_user = await self.client.fetch_user(Warning_deleted[0])
        reason = Warning_deleted[1]
        cur.execute("DELETE from warnings WHERE id = (?)", (warn_id, ))
        con.commit()
        warn_delete_embed = discord.Embed(title=f"Warning #{warn_id} deleted.",
                                          description=f"{warned_user.display_name} was warned for {reason}")
        warn_delete_embed.set_author(name=f"Deleted by {interaction.user.display_name}", icon_url=interaction.user.display_avatar)
        warn_delete_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))

        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])
        await modlog_channel.send(embed=warn_delete_embed)
        await interaction.response.send_message(embed=warn_delete_embed)
    
    @app_commands.command(name="warnings", description="Check all warnings in this server.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The user you want to check the warnings of")
    async def warnings(self, interaction: discord.Interaction, member: discord.User=None) -> None:
        warnings_embed = discord.Embed()
        if member is not None:
            cur.execute("SELECT id, reason, user FROM warnings WHERE user = ? AND guild = ?", (member.id, interaction.guild.id))
            warnings_embed.title = f"Warnings for {member.display_name}"
            warnings_embed.set_author(name=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar)
            warnings_embed.set_footer(text=datetime.now().strftime('%d/%m/%Y %H:%M'))
            warnings = cur.fetchall()
            if len(warnings) == 0:
                await interaction.response.send_message(f"{member.display_name} has no warnings yet.", ephemeral=True)
            await self.show(interaction, warnings, member)
        else:
            warnings = cur.execute("SELECT id, reason, user FROM warnings WHERE guild = ?", (interaction.guild.id, )).fetchall()
            await self.show(interaction, warnings, member)

    @timeout.error
    @ban.error
    @unban.error
    @kick.error
    @warn.error
    async def moderation_errors(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You're missing permissions to run this command!", ephemeral=True)

    async def show(self, interaction: discord.Interaction, warnings: list, member: discord.User=None):
        async def get_page(page: int):
            L = 10
            offset = (page-1) * L
            emb = discord.Embed()
            if member is not None:
                emb.title="ModLog Warnings for:"
                emb.description=member.mention
            else:
                emb.title=f"Modlogs for {interaction.guild.name}"
            for warning in warnings[offset:offset+L]:
                user = await self.client.fetch_user(warning[2])
                if member is None:
                    emb.add_field(name=f"ID: #{warning[0]}",value=f"Offender: {user.display_name}\n{warning[1]}", inline=False)
                else:
                    emb.add_field(name=f"ID: #{warning[0]}",value=f"{warning[1]}", inline=False)
            emb.set_author(name=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.avatar)
            n = Pagination.compute_total_pages(len(warnings), L)
            emb.set_footer(text=f"Page {page} from {n}")
            return emb, n

        await Pagination(interaction, get_page).navegate()


async def setup(client: commands.Bot):
    await client.add_cog(moderation(client))