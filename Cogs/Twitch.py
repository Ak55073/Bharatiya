import asyncio

import discord
import requests
from discord.ext import commands


class Twitch(commands.Cog):
    def __init__(self, bot, header, server, channel):
        self.bot = bot
        self.headers = header
        self.server = server
        self.channel = channel

    @commands.command()
    async def stream(self, ctx):
        username = str(ctx.message.content)[8:]

        # User Data
        url = 'https://api.twitch.tv/helix/users?login=' + username
        response = requests.get(url, headers=self.headers)
        data_user = dict(response.json())

        # Live Status
        url = 'https://api.twitch.tv/helix/streams?user_login=' + data_user['data'][0]['login']
        response = requests.get(url, headers=self.headers)
        live = dict(response.json())

        if not live['data']:
            await self.offline_status(username, 0, data_user, ctx=ctx)
        else:
            await self.online_status(username, 0, data_user, live, ctx=ctx)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if str(after.guild) == self.server and after.bot is False:
            if (before.activity is not None and after.activity is not None) and before.activity.type != after.activity.type:
                if str(after.activity.type) == "ActivityType.streaming":
                    await self.online(after.activity.url.split("/")[-1])

                elif str(before.activity.type) == "ActivityType.streaming":
                    await self.offline(before.activity.url.split("/")[-1])

            elif before.activity is None and (
                    after.activity is not None and str(after.activity.type) == "ActivityType.streaming"):
                await self.online(after.activity.url.split("/")[-1])

            elif after.activity is None and (
                    before.activity is not None and str(before.activity.type) == "ActivityType.streaming"):
                await self.offline(before.activity.url.split("/")[-1])

    async def offline(self, username):
        # User Data
        url = 'https://api.twitch.tv/helix/users?login=' + username
        response = requests.get(url, headers=self.headers)
        data_user = dict(response.json())
        await self.offline_status(username, 1, data_user)

    async def online(self, username):
        # User Data
        url = 'https://api.twitch.tv/helix/users?login=' + username
        response = requests.get(url, headers=self.headers)
        data_user = dict(response.json())

        # Live Status
        url = 'https://api.twitch.tv/helix/streams?user_login=' + data_user['data'][0]['login']
        response = requests.get(url, headers=self.headers)
        live = dict(response.json())

        inc = 0
        while not live['data']:
            if inc == 180:  # Exit after 30 min : 180 x 10 = 1800 / 60 = 30min
                break

            response = requests.get(url, headers=self.headers)
            live = dict(response.json())
            await asyncio.sleep(10)
            inc += 1

        await self.online_status(username, 1, data_user, live)

    async def offline_status(self, username, flag, datauser, ctx=None):
        embed = discord.Embed(title=str(datauser['data'][0]['display_name']).capitalize() + " will be back soon!",
                              description="https://www.twitch.tv/" + datauser['data'][0]['login'], color=0xcc0099)
        embed.set_thumbnail(url=datauser['data'][0]['profile_image_url'])
        embed.set_author(name="Views: " + str(datauser['data'][0]['view_count']),
                         icon_url="https://images-ext-1.discordapp.net/external/IZEY6CIxPwbBTk-S6KG6WSMxyY5bUEM"
                                  "-annntXfyqbw/https/cdn.discordapp.com/emojis/287637883022737418.png")
        embed.set_image(url=datauser['data'][0]['offline_image_url'])
        embed.set_footer(text="Offline", icon_url="https://img.icons8.com/metro/1600/offline.png")

        if str(datauser['data'][0]['broadcaster_type']) != "":
            embed.add_field(name='Broadcaster Type: ', value=str(datauser['data'][0]['broadcaster_type']).capitalize(),
                            inline=False)

        if flag == 0:
            await ctx.send("If user is online, Please wait 3min for API to Update")
            await ctx.send(embed=embed)

        else:
            stream_channel = self.bot.get_channel(self.channel)
            await stream_channel.send(username.capitalize() + " will be back soon!")
            await stream_channel.send(embed=embed)

    async def online_status(self, username, flag, datauser, live, ctx=None):
        embed = discord.Embed(title=str(datauser['data'][0]['display_name']).capitalize() + " is streaming!",
                              description="https://www.twitch.tv/" + datauser['data'][0]['login'], color=0xcc0099)
        embed.set_thumbnail(url=datauser['data'][0]['profile_image_url'])
        embed.set_author(name="Views: " + str(datauser['data'][0]['view_count']) + " | Live viewer count: " + str(
            live['data'][0]['viewer_count']),
                         icon_url="https://images-ext-1.discordapp.net/external/IZEY6CIxPwbBTk-S6KG6WSMxyY5bUEM"
                                  "-annntXfyqbw/https/cdn.discordapp.com/emojis/287637883022737418.png")

        if str(datauser['data'][0]['broadcaster_type']) != "":
            embed.add_field(name='Broadcaster Type: ', value=str(datauser['data'][0]['broadcaster_type']).capitalize(),
                            inline=False)

        # Game Data
        url = 'https://api.twitch.tv/helix/games?id=' + live['data'][0]['game_id']
        response = requests.get(url, headers=self.headers)
        game_lc = dict(response.json())

        embed.add_field(name="Playing:", value=game_lc['data'][0]['name'], inline=False)

        path = live['data'][0]['thumbnail_url']
        path = path.replace("{width}", "1920")
        path = path.replace("{height}", "1080")
        embed.set_image(url=path)

        embed.add_field(name="Stream Title:", value=live['data'][0]['title'], inline=False)
        embed.set_footer(text="Live | " + "Started: " + str(live['data'][0]['started_at'])[:10] + " Time: " + str(
            live['data'][0]['started_at'])[11:].replace("Z", " UTC"),
                         icon_url="https://static.thenounproject.com/png/594409-200.png")
        if flag == 0:
            await ctx.send("**" + username.capitalize() +
                           " is live.**\nSupport their stream at <https://www.twitch.tv/"
                           + username + ">")
            await ctx.send(embed=embed)

        else:
            stream_channel = self.bot.get_channel(self.channel)
            await stream_channel.send("**" + username.capitalize()
                             + " is live.**\nSupport their stream at <https://www.twitch.tv/"
                             + username + ">")
            await stream_channel.send(embed=embed)
