import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone


server = discord.Object(1352389107778846831)
con = sqlite3.connect("moderation.db")
cur = con.cursor()
i = 0

@app_commands.guilds(server)
class log(commands.GroupCog, group_name='log'):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="fetch_channels", description="Gets all channels from the server it's used in")
    @app_commands.checks.has_permissions(administrator=True)
    async def FetchChannels(self, interaction: discord.Interaction):   
        await interaction.response.defer() 
        channels = interaction.guild.channels
        for channel in channels:
            try:
                cur.execute("INSERT INTO channels (Name, ChannelID, GuildID) VALUES (?, ?, ?)", (channel.name, channel.id, channel.guild.id))
                con.commit()
            except sqlite3.IntegrityError:
                continue
        await interaction.followup.send("All new channels have been fetched!")

    @app_commands.command(name="set_log_channel", description="Sets the channel where the bot logs members joining and leaving.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Join log", value="join_channel"),
        app_commands.Choice(name="ModLog log", value="modlog_channel"),
        app_commands.Choice(name="Member log", value="member_channel"),
        app_commands.Choice(name="Message log", value="message_channel"),
        app_commands.Choice(name="Voice log", value="voice_channel"),
        app_commands.Choice(name="Server log", value="server_channel"),
        app_commands.Choice(name="Adult log", value="adult_channel")
    ])
    async def set_log_channel(self, interaction: discord.Interaction, type: app_commands.Choice[str], channel: discord.TextChannel=None):
        if (channel is not None):
            cur.execute("UPDATE channels SET type = (?) WHERE ChannelID = (?) AND GuildID = (?)", (type.value, channel.id, channel.guild.id))
            con.commit()
            await interaction.response.send_message(f"{type.name}s channel set to {channel.mention}")
        else:
            cur.execute("UPDATE channels SET type = (?) WHERE type = (?)", (None, type.value))
            con.commit()
            await interaction.response.send_message(f"The channel for {type.name}s has been cleared.")

    def get_channel(self, type: str, GuildID: int=server.id):
        cur.execute("SELECT Name FROM channels WHERE type = (?) AND GuildID = (?)", (type, GuildID))
        channelName = cur.fetchone()
        return channelName
        

#Join_channel logs.
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        join_embed = discord.Embed(title="Member joined")
        join_embed.set_author(name=member._user.name, icon_url=member.avatar)
        join_embed.description = f"{member.mention} {len(member.guild.members)}th to join\ncreated <t:{int(member.created_at.timestamp())}:R>"
        join_embed.set_footer(text=f"ID: {member.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        channelName = self.get_channel("join_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        await channel.send(embed=join_embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        now = datetime.now(tz=timezone.utc)
        leave_embed = discord.Embed(title="Member left")
        leave_embed.set_author(name=member._user.name, icon_url=member.avatar)
        role_string = ""
        for role in member.roles:
            if (role.name == "@everyone"):
                continue
            else:
                role_string += f"{role.mention}, "
        leave_embed.description = f"{member.mention} joined <t:{int(member.joined_at.timestamp())}:R>\n**Roles:** {role_string[:-2]}"
        leave_embed.set_footer(text=f"ID: {member.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        channelName = self.get_channel("join_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        await channel.send(embed=leave_embed)

        audit_log_embed = discord.Embed()
        modlog_channel_name = self.get_channel("modlog_channel")
        modlog_channel = discord.utils.get(self.client.get_all_channels(), name=modlog_channel_name[0])
        async for entry in self.client.get_guild(server.id).audit_logs(action=discord.AuditLogAction.ban):
            if (entry.user.id != 1312230111621156944 and entry.created_at >= (now - timedelta(seconds=15))):
                audit_log_embed.title = f"{entry.target.name} was banned"
                audit_log_embed.set_author(name=f"banned by {entry.user.display_name}", icon_url=entry.user.display_avatar)
                audit_log_embed.set_footer(text=f"ID: {member.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                if entry.reason:
                    audit_log_embed.description = entry.reason
                await modlog_channel.send(embed=audit_log_embed)
            break
        async for entry in self.client.get_guild(server.id).audit_logs(action=discord.AuditLogAction.kick):
            if (entry.user.id != 1312230111621156944 and entry.created_at >= (now - timedelta(seconds=15))):
                audit_log_embed.title = f"{entry.target.name} was kicked"
                audit_log_embed.set_author(name=f"Kicked by {entry.user.display_name}", icon_url=entry.user.display_avatar)
                audit_log_embed.set_footer(text=f"ID: {member.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                if entry.reason:
                    audit_log_embed.description = entry.reason
                await modlog_channel.send(embed=audit_log_embed)
            break

#Message_channel logs.
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):        
        message_edit_embed = discord.Embed(title=f"{after.author.display_name} their message was edited in {after.channel.name}")
        message_edit_embed.url = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"
        message_edit_embed.description = f"**Before:** {before.content}\n**+After:** {after.content}"
        message_edit_embed.set_footer(text=f"ID: {after.author.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        channelName = self.get_channel("message_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        adult_logs = self.get_channel("adult_channel")
        adult_channel = discord.utils.get(self.client.get_all_channels(), name = adult_logs[0])    

        if before.channel.is_nsfw() or after.channel.is_nsfw():
            return await adult_channel.send(embed=message_edit_embed)
        else:
            if (before.content == after.content):
                return
            else:
                return await channel.send(embed=message_edit_embed)
        

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        message_delete_embed = discord.Embed(title=f"Message deleted in {message.channel.name}")
        message_delete_embed.set_author(name=f"{message.author.name}", icon_url=message.author.avatar)
        message_delete_embed.description = f"{message.content}\n\nMessage ID: {message.id}"
        message_delete_embed.set_footer(text=f"ID: {message.author.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        channelName = self.get_channel("message_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        adult_logs = self.get_channel("adult_channel")
        adult_channel = discord.utils.get(self.client.get_all_channels(), name = adult_logs[0])

        if message.channel.id == channel.id or message.channel.id == adult_channel.id:
            return
        else:
            if message.channel.is_nsfw():
                return await adult_channel.send(embed=message_delete_embed)
            else:
                return await channel.send(embed=message_delete_embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        voice_embed = discord.Embed()
        voice_embed.set_author(name=f"{member.global_name}", icon_url=member.avatar)
        channelName = self.get_channel("voice_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name=channelName[0])
        if (before.channel is None and after.channel is not None):
            voice_embed.title = "Member joined voice channel"
            voice_embed.description = f"{member.mention} joined {after.channel.mention}"
            voice_embed.set_footer(text=f"ID: {after.channel.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            await channel.send(embed=voice_embed)
        elif (before.channel is not None and after.channel is None):
            voice_embed.title = "Member left voice channel"
            voice_embed.description = f"{member.mention} left {before.channel.mention}"
            voice_embed.set_footer(text=f"ID: {before.channel.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            await channel.send(embed=voice_embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        channelName = self.get_channel("member_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        member_update_embed = discord.Embed()
        member_update_embed.set_author(name=f"{after.display_name}", icon_url=after.avatar)
        member_update_embed.set_footer(text=f"ID: {after.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        if before.nick != after.nick:
            member_update_embed.title="Name change"
            member_update_embed.description = f"**Before:** {before.display_name}\n**+After:** {after.display_name}"
            return await channel.send(embed=member_update_embed)

        added_roles = set(after.roles) - set(before.roles)
        added_roles_string = ""
        removed_roles = set(before.roles) - set(after.roles)
        removed_roles_string = ""

        if before.is_timed_out() == False and after.is_timed_out() == True:
            member_update_embed.description = f"{after.mention} was timed out until     t:{int(after.timed_out_until.timestamp())}:f>"
        
        if before.is_timed_out() == True and after.is_timed_out() == False:
            member_update_embed.description = f"{after.mention} had their timeout removed"

        for role in added_roles:
            added_roles_string += f"{role.mention} "

        for role in removed_roles:
            removed_roles_string += f"{role.mention} "

        if added_roles:
            member_update_embed.title = "Role added"
            member_update_embed.description = added_roles_string
        
        if removed_roles:
            member_update_embed.title = "Role removed"
            member_update_embed.description = removed_roles_string

        if removed_roles or added_roles:
            return await channel.send(embed=member_update_embed)

        if before.avatar == after.avatar:
            return
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        channelName = self.get_channel("server_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        new_role_embed = discord.Embed(title="New role created")
        new_role_embed.description = f"**Name:** {role.name}\n**Color:** {role.color}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}"
        new_role_embed.set_footer(text=f"{role.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await channel.send(embed=new_role_embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        channelName = self.get_channel("server_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        role_deleted_embed = discord.Embed(title=f'Role "{role.name}" removed')
        role_deleted_embed.description = f"**Name:**{role.name}\n**Color:**{role.color}\n**Mentionable:**{role.mentionable}\n**Displayed separately:**{role.hoist}\n**Position:**{role.position}"
        role_deleted_embed.set_footer(text=f"{role.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await channel.send(embed=role_deleted_embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        channelName = self.get_channel("server_channel")
        channel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])
        updated_permissions_embed = discord.Embed(title=f'Role "{after.name}" updated')

        if (before.name != after.name):
            updated_permissions_embed.add_field(name="**Before**", value=f"**Name:** {before.name}")
            updated_permissions_embed.add_field(name="**After**", value=f"**Name:** {after.name}")
        
        if (before.color != after.color):
            updated_permissions_embed.add_field(name="**Before**", value=f"**Name:** {before.color}")
            updated_permissions_embed.add_field(name="**After**", value=f"**Name:** {after.color}")

        permissions = set(after.permissions) - set(before.permissions)
        added_perms = []
        removed_perms = []
        for permission in permissions:
            if (permission[1]):
                added_perms.append(permission[0])
            else:
                removed_perms.append(permission[0])
        added_perms_string = ""
        removed_perms_string = ""
        for i in range(len(added_perms)):
            added_perms_string += f"{added_perms[i].replace('_', ' ')}, "
        for i in range(len(removed_perms)):
            removed_perms_string += f"{removed_perms[i].replace('_', ' ')}, "
        if (len(added_perms) == 0):
            updated_permissions_embed.add_field(name="**New permissions**", value=f"**Removed:** {removed_perms_string[:-2]}")
        elif (len(removed_perms) == 0):
            updated_permissions_embed.add_field(name="**New permissions**", value=f"**Added:** {added_perms_string[:-2]}")
        else:
            updated_permissions_embed.add_field(name="**New permissions**", value=f"**Added:** {added_perms_string[:-2]}\n**Removed:** {removed_perms_string[:-2]}")
        updated_permissions_embed.set_footer(text=f"Role ID: {after.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await channel.send(embed=updated_permissions_embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        channelName = self.get_channel("server_channel")
        logChannel = discord.utils.get(self.client.get_all_channels(), name = channelName[0])

        new_channel_embed = discord.Embed(title=f"{channel.type.name.capitalize()} channel created")
        discord.Permissions.send_messages
        new_channel_embed.add_field(name=f"**Name:** {channel.name}", value=f"**Category:** {channel.category.name}", inline=False)
        new_channel_embed.set_footer(text=f"Channel ID: {channel.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        await logChannel.send(embed=new_channel_embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        channelName = self.get_channel("server_channel")
        logChannel = discord.utils.get(self.client.get_all_channels(), name = channelName)

        new_channel_embed = discord.Embed(title=f"{channel.type.name.capitalize()} channel deleted")
        discord.Permissions.send_messages
        new_channel_embed.add_field(name=f"**Name:** {channel.name}", value=f"**Category:** {channel.category.name}", inline=False)
        new_channel_embed.set_footer(text=f"Channel ID: {channel.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        await logChannel.send(embed=new_channel_embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        now = datetime.now(tz=timezone.utc)
        channelName = self.get_channel("server_channel")
        logChannel = discord.utils.get(self.client.get_all_channels(), name=channelName[0])
        update_channel_embed = discord.Embed(title=f"{after.type.name.capitalize()} channel updated")
        update_channel_embed.set_footer(text=f"Channel ID: {after.id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        sorted_before = sorted(before.overwrites, key=lambda x: x.id)
        sorted_after = sorted(after.overwrites, key=lambda x: x.id)

        try:
            for (before_role, after_role) in zip(sorted_before, sorted_after):
                before_value = before.overwrites[before_role]
                after_value = after.overwrites[after_role]
                if before_role.name == "@everyone" or after_role.name == "@everyone": 
                    update_channel_embed.description = f"**Overwrites for {after_role.name} in {after.mention} updated**"
                else:
                    update_channel_embed.description = f"**Overwrites for {after_role.mention} in {after.mention} updated**"
                global has_updates
                has_updates = False
                for after1, before1 in zip(sorted(after_value), sorted(before_value)):
                        if (after1 is None and before1 is None):
                            continue
                        if (after1 == before1):
                            continue
                        else:
                            has_updates = True
                            emoji_before = ":white_check_mark:"
                            emoji_after = ":x:" 
                            if after1[1]:
                                emoji_before, emoji_after = emoji_after, emoji_before
                            update_channel_embed.add_field(name=f"{after1[0]}: {emoji_before} -> {emoji_after}", value="", inline=False)
                if (has_updates):
                    await logChannel.send(embed=update_channel_embed)
        except Exception as e:
            print(e.args)


async def setup(client: commands.Bot):
    await client.add_cog(log(client))