import datetime
import os
from json import loads

import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, CommandInvokeError, has_permissions

from Driver.dbdriver import DBManage


class ServerListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            data = loads(open("config.json", "r").read())
            self.DatabaseHelper = DBManage(url=data["MONGO"])
        except FileNotFoundError:
            self.DatabaseHelper = DBManage(url=os.getenv("MONGO"))

    @staticmethod
    async def member_notification(member, new_member_notification, mode):
        embed = discord.Embed(title=("(" + str(member.id) + ")"), description="\u200b", color=0x00ff00)

        dates = (
            str(datetime.date.today()).split("-"),  # Today's date
            str(member.created_at).split(" ")[0].split("-") if mode == "join"  # Date of creation
            else str(member.joined_at).split(" ")[0].split("-")  # Data of joining server
        )  # Formatting to [yyyy,mm,dd]

        days = str(
            datetime.date(int(dates[0][0]), int(dates[0][1]), int(dates[0][2])) -  # Today's date
            datetime.date(int(dates[1][0]), int(dates[1][1]), int(dates[1][2]))  # Date of creation or Date of Joining
        )  # Days since account was created or user joined server

        txt_msg = None
        if mode == "join":  # Member joining server.
            embed.set_author(name=member.display_name + " has joined " + str(member.guild), url="")

            embed.add_field(name='Joined ' + str(member.guild) + ' on',
                            value=(str(datetime.datetime.now())[:16]),
                            inline=False)
            embed.add_field(name='Account Created on',
                            value=(str(member.created_at)[:16] + "\n" + days.split(",")[0] + " ago"),
                            inline=False)

            txt_msg = "Welcome " + member.mention + " to " + str(member.guild)

            if new_member_notification["message"] is not None:
                txt_msg += ". " + new_member_notification["message"]
            else:
                txt_msg += ". Enjoy your stay."

            if new_member_notification["role"] is not None:
                role_assign = discord.utils.get(member.guild.roles, name=new_member_notification["role"])
                await member.add_roles(role_assign)

        else:
            embed.set_author(name=member.display_name + " has left " + str(member.guild), url="")

            embed.add_field(
                name='Left ' + str(member.guild) + ' on',
                value=(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                           + "\nBeen Member for \n" + days.split(",")[0])),
                inline=False)

        if member.avatar_url == "":
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/avatars/429945357808697355"
                    "/1610303189d607b5665cba3d037226b7.webp?size=128")
        else:
            embed.set_thumbnail(url=member.avatar_url)

        embed.set_footer(text="Bhartiya", icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                                   "/1610303189d607b5665cba3d037226b7.webp?size=128")

        channel = discord.utils.get(member.guild.text_channels, name=new_member_notification["channel"])
        if txt_msg:
            await channel.send(txt_msg)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        new_member_notification = self.DatabaseHelper.server_query_data(member.guild.id, "new_member")
        if new_member_notification['enable']:
            await self.member_notification(member, new_member_notification, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        new_member_notification = self.DatabaseHelper.server_query_data(member.guild.id, "new_member")
        if new_member_notification['enable']:
            await self.member_notification(member, new_member_notification, "leave")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        new_member = self.DatabaseHelper.server_query_data(channel.guild.id, "new_member")
        if new_member["enable"] and channel.name == new_member["channel"]:
            self.DatabaseHelper.server_update_member(
                guild_id=channel.guild.id,
                append_message=None,
                role=None,
                channel=None,
                enable=False)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name == after.name:
            return
        new_member = self.DatabaseHelper.server_query_data(after.guild.id, "new_member")
        if new_member["enable"]  and before.name == new_member["channel"]:
            self.DatabaseHelper.server_update_member(
                guild_id=after.guild.id,
                append_message=new_member["message"],
                role=new_member["role"],
                channel=after.name,
                enable=new_member["enable"])

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        new_member = self.DatabaseHelper.server_query_data(role.guild.id, "new_member")
        if new_member["enable"] and role.name == new_member["role"]:
            self.DatabaseHelper.server_update_member(
                guild_id=role.guild.id,
                append_message=None,
                role=None,
                channel=None,
                enable=False)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.name == after.name:
            return
        new_member = self.DatabaseHelper.server_query_data(after.guild.id, "new_member")
        if new_member["enable"] and before.name == new_member["role"]:
            self.DatabaseHelper.server_update_member(
                guild_id=after.guild.id,
                append_message=new_member["message"],
                role=after.name,
                channel=new_member["channel"],
                enable=new_member["enable"])

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def set_member_welcome(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        while True:
            # Message to be appended with welcome message
            message = "Welcome to member join/leave configuration prompt.```cs\n" \
                      "Specify a custom message to be append with welcome message. \n" \
                      "Type \"skip\" or \"none\" to use default message.\n" \
                      "Type \"exit\" to cancel prompt.\n\n" \
                      "# Example: \n" \
                      "Welcome {user} to {guild}. [Append Message]```".format(user=ctx.message.author.name,
                                                                              guild=ctx.guild.name)
            await ctx.send(message)

            append_message = await self.bot.wait_for('message', check=check, timeout=60)
            if append_message.content.lower() in ["none", "skip"]:
                append_message = None
                break
            elif append_message.content.lower() in ["exit"]:
                await ctx.send("Member notification prompt cancelled.")
                return

            await ctx.send("Confirm **" + append_message.content + "** ?\n(Y:Yes|N:NO)")
            prompt = await self.bot.wait_for('message', check=check, timeout=60)
            if prompt.content.lower() == "y":
                break

        # Role to assign on join
        message = "Specify a role to auto-assign member on joining.```cs\n" \
                  "> Role must already exist.\n" \
                  "> Do not tag the role. Enter role name only.\n" \
                  "> Text is case sensitive.\n" \
                  "Type \"skip\" or \"none\" to not assign any role on joining.\n" \
                  "Type \"exit\" to cancel prompt```"
        await ctx.send(message)
        while True:
            assign_role = await self.bot.wait_for('message', check=check, timeout=60)

            if assign_role.content.lower() in ["skip", "none"]:
                assign_role = None
                break
            elif assign_role.content.lower() in ["exit"]:
                await ctx.send("Member notification prompt cancelled.")
                return

            assign_role = discord.utils.get(ctx.guild.roles, name=assign_role.content)
            if assign_role:
                break
            else:
                await ctx.send(
                    "**Error 404: Role does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

        # Channel to send notification
        message = "Specify a **channel name** to send welcome message.```cs\n" \
                  "> Channel must already exist.\n" \
                  "> Do not tag the channel. Enter channel name only.\n" \
                  "> Text is case sensitive.\n" \
                  "Type \"skip\", \"none\" or \"exit\" to cancel prompt.```"

        await ctx.send(message)
        while True:
            channel_name = await self.bot.wait_for('message', check=check, timeout=60)

            if channel_name.content.lower() in ["skip", "none", "exit"]:
                await ctx.send("Can't enable this feature without a valid channel.")
                return

            channel_name = discord.utils.get(ctx.guild.text_channels, name=channel_name.content)
            if channel_name:
                break
            else:
                await ctx.send(
                    "**Error 404: Channel does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

        data = {
            "enable": True,
            "message": append_message.content if append_message else None,
            "role": assign_role.name if assign_role else None,
            "channel": channel_name.name
        }
        await self.member_notification(ctx.author, data, "join")

        await ctx.send("Confirm preview sent to #" + channel_name.name + " ?\n(Y:Yes|R:Restart|N:No)")
        prompt = await self.bot.wait_for('message', check=check, timeout=60)
        if prompt.content.lower() == "y":
            self.DatabaseHelper.server_update_member(
                guild_id=ctx.guild.id,
                append_message=append_message.content if append_message else None,
                role=assign_role.name if assign_role else None,
                channel=channel_name.name)
            await ctx.send("Configuration saved successfully.\n"
                           "Use >help_member_welcome for more information.")

        elif prompt.content.lower() == "r":
            await self.set_member_welcome(ctx)
            return

        else:
            await ctx.send("Member notification prompt cancelled.")

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def remove_member_welcome(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "Do you wish to remove new member join/leave notifications?\n(Y:YES|N:NO)"
        await ctx.send(message)
        prompt = await self.bot.wait_for('message', check=check, timeout=30)
        if prompt.content.lower() in ["yes", "y"]:
            self.DatabaseHelper.server_update_member(
                guild_id=ctx.guild.id,
                append_message=None,
                role=None,
                channel=None,
                enable=False
            )
            await ctx.send("New member notification deactivated.\n"
                           "Use >help_member_welcome for more information.")
        else:
            await ctx.send("Prompt cancelled.")

    @set_member_welcome.error
    @remove_member_welcome.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("To prevent spam. Only administrator can use this command.")
        elif isinstance(error, CommandInvokeError):
            await ctx.send("Did not receive any reply from user. Exiting config prompt.")

    @commands.command(pass_context=True)
    async def help_member_welcome(self, ctx):
        member_welcome = self.DatabaseHelper.server_query_data(ctx.guild.id, mode="new_member")
        embed = discord.Embed(title="Member Join/Leave Notification", description="\u200b",
                              color=0xcc0099)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad.webp")

        if member_welcome["enable"]:
            embed.add_field(name='Role:',
                            value=member_welcome["role"],
                            inline=True)
            embed.add_field(name='Channel',
                            value=member_welcome["channel"],
                            inline=True)
            embed.add_field(name='Message',
                            value=member_welcome["message"],
                            inline=True)

            embed.add_field(name='\u200b',
                            value="Commands",
                            inline=False)
            embed.add_field(name='>set_member_welcome',
                            value='Update settings for member notification.',
                            inline=False)
            embed.add_field(name='>remove_member_welcome',
                            value='Disable member notification from this server.',
                            inline=False)
        else:
            embed.add_field(name='Member Notification: Disable',
                            value="Use >set_member_welcome to enable.",
                            inline=False)
        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/"
                                  "216236803710124032/287ada789e1944a72a2f826e229cba29.webp")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(ServerListener(bot))