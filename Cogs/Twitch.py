import os
from json import loads

import discord
import requests
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions, CommandInvokeError
from discord.ext.tasks import loop

from Driver.dbdriver import DBManage


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        try:
            data = loads(open("config.json", "r").read())
            self.DatabaseHelper = DBManage(url=data["MONGO"])
            self.headers = data["TWITCH"]
        except FileNotFoundError:
            self.DatabaseHelper = DBManage(url=os.getenv("MONGO"))
            self.headers = loads(os.environ["TWITCH"])

        self.stream_list = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        self.schedule_notification.start()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not after.bot and \
                after.activity is not None and \
                before.activity != after.activity and \
                str(after.activity.type) == "ActivityType.streaming":
            data = self.DatabaseHelper.member_query_data(member_id=after.id, mode="one")
            if not data:
                self.DatabaseHelper.member_add_data(
                    member_id=after.id,
                    twitch_username=after.activity.url.split("/")[-1],
                    guild_id=after.guild.id)
                # "after.activity.url.split("/")[-1]" reading user's Twitch username through activity
            else:
                if not data["in_server"]:
                    self.DatabaseHelper.member_update_server(
                        member_id=after.id,
                        server_list=[after.guild.id, ],
                        blocked_list=None)
                elif after.guild.id not in data["in_server"]:
                    data["in_server"].append(after.guild.id)
                    self.DatabaseHelper.member_update_server(
                        member_id=after.id,
                        server_list=data["in_server"],
                        blocked_list=None)

    @loop(minutes=15)
    async def schedule_notification(self):
        # Member Stream
        member_data = self.DatabaseHelper.member_query_data(member_id=None, mode="all")
        for member in member_data:
            url = 'https://api.twitch.tv/helix/streams?user_login=' + member["twitch_username"]
            response = requests.get(url, headers=self.headers)
            live = dict(response.json())
            server_list = [server for server in member["in_server"] if server not in member["blocked_from"]]

            if live['data'] and not member["live_status"]:
                self.DatabaseHelper.member_update_status(member["id"], True)
                data_user = None
                game_lc = None
                for server_id in server_list:
                    server_data = self.DatabaseHelper.server_query_data(server_id, "twitch")
                    if server_data and server_data["enable"]:
                        if not data_user:
                            # User Data
                            url = 'https://api.twitch.tv/helix/users?login=' + member["twitch_username"]
                            response = requests.get(url, headers=self.headers)
                            data_user = dict(response.json())

                            # Data about the game being streamed
                            url = 'https://api.twitch.tv/helix/games?id=' + live['data'][0]['game_id']
                            response = requests.get(url, headers=self.headers)
                            game_lc = dict(response.json())

                        server_ob = self.bot.get_guild(server_id)
                        channel = discord.utils.get(server_ob.text_channels, name=server_data["twitch_channel"])
                        await self.twitch_notification(data_user, channel, live, game_lc)

            elif not live['data'] and member["live_status"]:
                self.DatabaseHelper.member_update_status(member["id"], False)
                data_user = None
                for server_id in server_list:
                    server_data = self.DatabaseHelper.server_query_data(server_id, "twitch")
                    if server_data and server_data["enable"]:
                        if not data_user:
                            # User Data
                            url = 'https://api.twitch.tv/helix/users?login=' + member["twitch_username"]
                            response = requests.get(url, headers=self.headers)
                            data_user = dict(response.json())
                        server_ob = self.bot.get_guild(server_id)
                        channel = discord.utils.get(server_ob.text_channels, name=server_data["twitch_channel"])
                        await self.twitch_notification(data_user, channel)

        # Extra Stream
        data = self.DatabaseHelper.server_query_data(guild_id=None, mode='twitch_followed')
        for server_data in data:
            twitch_data = server_data["twitch_notification"]
            server = self.bot.get_guild(server_data["id"])
            channel_name = discord.utils.get(server.text_channels, name=twitch_data["twitch_channel"])
            for ind in range(0, len(twitch_data["other_streamer"])):
                url = 'https://api.twitch.tv/helix/streams?user_login=' + twitch_data["other_streamer"][ind]["username"]
                response = requests.get(url, headers=self.headers)
                live = dict(response.json())

                if live['data'] and not twitch_data["other_streamer"][ind]["live_status"]:
                    self.DatabaseHelper.server_update_twitch_streamer_status(
                        guild_id=server_data["id"],
                        pos=twitch_data["other_streamer"][ind]["username"],
                        live=True
                    )

                    # User Data
                    url = 'https://api.twitch.tv/helix/users?login=' + twitch_data["other_streamer"][ind]["username"]
                    response = requests.get(url, headers=self.headers)
                    data_user = dict(response.json())

                    # Data about the game being streamed
                    url = 'https://api.twitch.tv/helix/games?id=' + live['data'][0]['game_id']
                    response = requests.get(url, headers=self.headers)
                    game_lc = dict(response.json())

                    await self.twitch_notification(data_user, channel_name, live, game_lc)

                elif not live['data'] and twitch_data["other_streamer"][ind]["live_status"]:
                    self.DatabaseHelper.server_update_twitch_streamer_status(
                        guild_id=server_data["id"],
                        pos=twitch_data["other_streamer"][ind]["username"],
                        live=False
                    )
                    url = 'https://api.twitch.tv/helix/users?login=' + twitch_data["other_streamer"][ind]["username"]
                    response = requests.get(url, headers=self.headers)
                    data_user = dict(response.json())
                    await self.twitch_notification(data_user, channel_name)

    @staticmethod
    async def twitch_notification(data_user, channel, live=None, game_lc=None):
        if live:
            embed = discord.Embed(title=str(data_user['data'][0]['display_name']).capitalize() + " is streaming!",
                                  description="https://www.twitch.tv/" + data_user['data'][0]['login'], color=0xcc0099)
            embed.set_thumbnail(url=data_user['data'][0]['profile_image_url'])
            embed.set_author(name="Views: " + str(data_user['data'][0]['view_count']) + " | Live viewer count: " + str(
                live['data'][0]['viewer_count']),
                             icon_url="https://images-ext-1.discordapp.net/external/IZEY6CIxPwbBTk-S6KG6WSMxyY5bUEM"
                                      "-annntXfyqbw/https/cdn.discordapp.com/emojis/287637883022737418.png")

            if str(data_user['data'][0]['broadcaster_type']) != "":
                embed.add_field(name='Broadcaster Type: ',
                                value=str(data_user['data'][0]['broadcaster_type']).capitalize(),
                                inline=False)

            embed.add_field(name="Playing:", value=game_lc['data'][0]['name'], inline=False)

            path = live['data'][0]['thumbnail_url']
            path = path.replace("{width}", "1920")
            path = path.replace("{height}", "1080")
            embed.set_image(url=path)

            embed.add_field(name="Stream Title:", value=live['data'][0]['title'], inline=False)
            embed.set_footer(text="Live | " + "Started: " + str(live['data'][0]['started_at'])[:10] + " Time: " + str(
                live['data'][0]['started_at'])[11:].replace("Z", " UTC"),
                             icon_url="https://static.thenounproject.com/png/594409-200.png")

            await channel.send("**" + data_user['data'][0]['display_name'] +
                               " is live.**\nSupport their stream at <https://www.twitch.tv/"
                               + data_user['data'][0]['login'] + ">")
            await channel.send(embed=embed)

        else:
            embed = discord.Embed(title=str(data_user['data'][0]['display_name']).capitalize() + " will be back soon!",
                                  description="https://www.twitch.tv/" + data_user['data'][0]['login'], color=0xcc0099)
            embed.set_thumbnail(url=data_user['data'][0]['profile_image_url'])
            embed.set_author(name="Views: " + str(data_user['data'][0]['view_count']),
                             icon_url="https://images-ext-1.discordapp.net/external/IZEY6CIxPwbBTk-S6KG6WSMxyY5bUEM"
                                      "-annntXfyqbw/https/cdn.discordapp.com/emojis/287637883022737418.png")
            embed.set_image(url=data_user['data'][0]['offline_image_url'])
            embed.set_footer(text="Offline", icon_url="https://img.icons8.com/metro/1600/offline.png")

            if str(data_user['data'][0]['broadcaster_type']) != "":
                embed.add_field(name='Broadcaster Type: ',
                                value=str(data_user['data'][0]['broadcaster_type']).capitalize(),
                                inline=False)

            await channel.send("If user is online, Please wait 3min for API to Update")
            await channel.send(embed=embed)

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def set_twitch(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "Welcome to twitch configuration prompt.\n" \
                  "Specify a **channel name** to send twitch notification.```cs\n" \
                  "> Channel must already exist.\n" \
                  "> Do not tag the channel. Enter channel name only.\n" \
                  "> Text is case sensitive.\n" \
                  "Type \"exit\" or \"none\" to cancel prompt.```"
        await ctx.send(message)
        while True:
            channel_name = await self.bot.wait_for('message', check=check, timeout=60)

            if channel_name.content.lower() in ["skip", "none", "exit"]:
                await ctx.send("Twitch notification prompt cancelled.")
                return

            channel_name = discord.utils.get(ctx.guild.text_channels, name=channel_name.content)
            if channel_name:
                self.DatabaseHelper.server_update_twitch(
                    guild_id=ctx.guild.id,
                    channel=channel_name.name)
                await ctx.send("Configuration saved successfully.\n"
                               "Use >help_twitch for more information.")
                return
            else:
                await ctx.send(
                    "**Error 404: Channel does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def twitch_block_user(self, ctx):
        if not ctx.message.mentions:
            await ctx.send("Please tag the user. Do not write username")
            return
        for user in ctx.message.mentions:
            member_data = self.DatabaseHelper.member_query_data(user.id, "one")
            if member_data:
                if not member_data["blocked_from"]:
                    self.DatabaseHelper.member_update_server(
                        member_id=user.id,
                        blocked_list=[ctx.guild.id, ],
                        server_list=None
                    )
                    await ctx.send("Twitch notification for given user will not be sent.")
                elif user.id not in member_data["blocked_from"]:
                    member_data["blocked_from"].append(ctx.guild.id)
                    self.DatabaseHelper.member_update_server(
                        member_id=user.id,
                        blocked_list=member_data["blocked_from"],
                        server_list=None
                    )
                    await ctx.send("Twitch notification for given user will not be sent.")
                else:
                    await ctx.send("User already blocked.")
            else:
                await ctx.send("User not a streamer.")

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def twitch_unblock_user(self, ctx):
        if not ctx.message.mentions:
            await ctx.send("Please tag the user. Do not write username")
            return

        for user in ctx.message.mentions:
            member_data = self.DatabaseHelper.member_query_data(user.id, "one")
            if member_data:
                if member_data["blocked_from"]:
                    if user.id in member_data["blocked_from"]:
                        member_data["blocked_from"].remove(ctx.guild.id)
                        self.DatabaseHelper.member_update_server(
                            member_id=user.id,
                            blocked_list=member_data["blocked_from"],
                            server_list=None
                        )
                        await ctx.send("Twitch notification for given user activated.")
                    else:
                        await ctx.send("User isn't blocked.")
                else:
                    await ctx.send("User isn't blocked.")
            else:
                await ctx.send("User not a streamer.")

    @commands.command(pass_context=True)
    async def stream_add(self, ctx, username):
        def check(msg):
            return msg.author == ctx.message.author

        twitch_data = self.DatabaseHelper.server_query_data(
            guild_id=ctx.guild.id,
            mode="twitch"
        )
        if twitch_data["enable"]:
            invalid_user = await self.check_stream(ctx, username)
            if invalid_user:
                return

            await ctx.send("Is this the user you are looking for?\n(Y:Yes|N:No)")
            prompt = await self.bot.wait_for('message', check=check, timeout=30)
            if prompt.content.lower() not in ["y", "yes"]:
                await ctx.send("Ensure twitch username is valid.\nUser not added.")
                return

            if not twitch_data["other_streamer"]:
                twitch_data["other_streamer"] = [username, ]
                self.DatabaseHelper.server_update_twitch_streamer(
                    guild_id=ctx.guild.id,
                    streamer=[{
                        "username": username,
                        "live_status": False
                    }, ]
                )
            elif username in [uname["username"] for uname in twitch_data["other_streamer"]]:
                await ctx.send("User is already followed in this server.")
                return
            else:
                user_data = {
                    "username": username,
                    "live_status": False
                }
                twitch_data["other_streamer"].append(user_data)
                self.DatabaseHelper.server_update_twitch_streamer(
                    guild_id=ctx.guild.id,
                    streamer=twitch_data["other_streamer"]
                )

            await ctx.send(username + " added to streamer list.")

        else:
            await ctx.send("Twitch notification disabled. Use >set_twitch")

    @commands.command(pass_context=True)
    async def stream_remove(self, ctx, username):
        twitch_data = self.DatabaseHelper.server_query_data(
            guild_id=ctx.guild.id,
            mode="twitch"
        )
        if twitch_data["enable"]:
            for ind in range(0, len(twitch_data["other_streamer"])):
                if twitch_data["other_streamer"][ind]["username"] == username:
                    del twitch_data["other_streamer"][ind]
                    break
            else:
                await ctx.send("User isn't followed.")
                return

            if not twitch_data["other_streamer"]:
                self.DatabaseHelper.server_update_twitch_streamer(
                    guild_id=ctx.guild.id,
                    streamer=None
                )
            else:
                self.DatabaseHelper.server_update_twitch_streamer(
                    guild_id=ctx.guild.id,
                    streamer=twitch_data["other_streamer"]
                )
            await ctx.send("Username removed from list.")

        else:
            await ctx.send("Twitch notification disabled. Use >set_twitch")

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def remove_twitch(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "Do you wish to remove twitch notification?\n(Y:YES|N:NO)"
        await ctx.send(message)
        prompt = await self.bot.wait_for('message', check=check, timeout=30)
        if prompt.content.lower() in ["yes", "y"]:
            self.DatabaseHelper.server_update_twitch(
                guild_id=ctx.guild.id,
                channel=None,
                enable=False
            )
            self.DatabaseHelper.server_update_twitch_streamer(
                guild_id=ctx.guild.id,
                streamer=None
            )
            await ctx.send("New member notification deactivated.")

    @set_twitch.error
    @remove_twitch.error
    @stream_add.error
    @stream_remove.error
    async def timeout_error(self, ctx, error):
        print(error)
        if isinstance(error, MissingPermissions):
            await ctx.send("To prevent data loss. Only user with administrator permission can use clear command.")
        elif isinstance(error, CommandInvokeError):
            await ctx.send("Did not receive any reply from user. Exiting config prompt.")

    @commands.command(pass_context=True)
    async def help_twitch(self, ctx):
        twitch = self.DatabaseHelper.server_query_data(ctx.guild.id, mode="twitch")
        embed = discord.Embed(title="Twitch Notification", description="\u200b",
                              color=0xcc0099)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad.webp")

        if twitch["enable"]:
            embed.add_field(name='Channel',
                            value=twitch["twitch_channel"],
                            inline=False)
            embed.add_field(name='Twitch user followed (Not in this server):',
                            value=twitch["other_streamer"] if twitch["other_streamer"] else "None",
                            inline=False)

            embed.add_field(name='\u200b',
                            value="Commands",
                            inline=False)
            embed.add_field(name='>set_twitch',
                            value='Update settings for twitch notification.',
                            inline=False)
            embed.add_field(name='>stream_add TWITCH_USER',
                            value='Follow a twitch user who is not in this server.',
                            inline=False)
            embed.add_field(name='>twitch_block_user MENTION_USER(S)',
                            value='Block twitch notification for a particular member in the server.',
                            inline=False)
            embed.add_field(name='>twitch_unblock_user MENTION_USER(S)',
                            value='Un-Block twitch notification for a particular member in the server.',
                            inline=False)
            embed.add_field(name='>stream_remove TWITCH_USER',
                            value='Unfollow twitch user from this server..',
                            inline=False)
            embed.add_field(name='>remove_twitch',
                            value='Disable twitch notification from this server.',
                            inline=False)
        else:
            embed.add_field(name='Member Notification: Disable',
                            value="Use >set_twitch to enable.",
                            inline=False)

        embed.add_field(name='>check_stream TWITCH_USERNAME',
                        value='Get real time information about twitch user.',
                        inline=False)

        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/"
                                  "216236803710124032/287ada789e1944a72a2f826e229cba29.webp")
        await ctx.send(embed=embed)

    @commands.command()
    async def check_stream(self, ctx, username):

        # User Data
        url = 'https://api.twitch.tv/helix/users?login=' + username
        response = requests.get(url, headers=self.headers)
        data_user = dict(response.json())

        if not data_user["data"]:
            await ctx.channel.send("**Error 404**: No user found.")
            return True

        # Live Status
        url = 'https://api.twitch.tv/helix/streams?user_login=' + username
        response = requests.get(url, headers=self.headers)
        live = dict(response.json())

        if live['data']:
            # Data about the game being streamed
            url = 'https://api.twitch.tv/helix/games?id=' + live['data'][0]['game_id']
            response = requests.get(url, headers=self.headers)
            game_lc = dict(response.json())

            await self.twitch_notification(data_user, ctx.channel, live, game_lc)

        else:
            await self.twitch_notification(data_user, ctx.channel)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        for member in guild.members:
            member_data = self.DatabaseHelper.member_query_data(member.id, "one")
            if member_data:
                member_data["in_server"].remove(guild.id)
                if member_data["blocked_from"] and guild.id in member_data["blocked_from"]:
                    member_data["blocked_from"].remove(guild.id)
                    self.DatabaseHelper.member_update_server(member_id=member.id,
                                                             server_list=member_data["in_server"],
                                                             blocked_list=member_data["blocked_from"])
                else:
                    self.DatabaseHelper.member_update_server(member_id=member.id,
                                                             server_list=member_data["in_server"],
                                                             blocked_list=None)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        member_data = self.DatabaseHelper.member_query_data(member_id=member.id, mode="one")
        if member_data and member.guild.id not in member_data["in_server"]:
            member_data["in_server"].append(member.guild.id)
            self.DatabaseHelper.member_update_server(member_id=member.id,
                                                     server_list=member_data["in_server"],
                                                     blocked_list=None)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        member_data = self.DatabaseHelper.member_query_data(member_id=member.id, mode="one")
        if member_data and member.guild.id in member_data["in_server"]:
            member_data["in_server"].remove(member.guild.id)
            if member_data["blocked_from"] and member.guild.id in member_data["blocked_from"]:
                member_data["blocked_from"].remove(member.guild.id)
                self.DatabaseHelper.member_update_server(member_id=member.id,
                                                         server_list=member_data["in_server"],
                                                         blocked_list=member_data["blocked_from"])
            else:
                self.DatabaseHelper.member_update_server(member_id=member.id,
                                                         server_list=member_data["in_server"],
                                                         blocked_list=None)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        server_data = self.DatabaseHelper.server_query_data(channel.guild.id, "twitch")
        if server_data["enable"] and channel.name == server_data["channel"]:
            self.DatabaseHelper.server_update_twitch(
                guild_id=channel.guild.id,
                channel=None,
                enable=False)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        server_data = self.DatabaseHelper.server_query_data(after.guild.id, "twitch")
        if server_data["enable"] and before.name != after.name and before.name == server_data["channel"]:
            self.DatabaseHelper.server_update_twitch(
                guild_id=after.guild.id,
                channel=after.name)


def setup(bot):
    bot.add_cog(Twitch(bot))
