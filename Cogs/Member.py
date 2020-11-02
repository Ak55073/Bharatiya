import datetime

import discord
from discord.ext import commands


class Member(commands.Cog):
    def __init__(self, bot, server):
        self.bot = bot
        self.server = server

    @commands.Cog.listener()
    async def on_member_join(self, member):
        now = str(datetime.datetime.now())
        time = str(member.created_at)
        compare = (str(datetime.date.today()).split("-"),  # Today's date
                   str(member.created_at).split(" ")[0].split("-"))  # Date of creation
        days = str(
            datetime.date(int(compare[0][0]), int(compare[0][1]), int(compare[0][2])) -  # Today's date
            datetime.date(int(compare[1][0]), int(compare[1][1]), int(compare[1][2])))  # Date of creation

        for gen in member.guild.channels:
            if "general" == str(gen):
                embed = discord.Embed(title=("(" + str(member.id) + ")"), description="\u200b", color=0x00ff00)
                embed.set_author(name=member.display_name + " has joined " + str(member.guild), url="")

                if member.avatar_url == "":
                    embed.set_thumbnail(
                        url="https://images-ext-1.discordapp.net/external/AsXVksCERNjwXR5gnT-oTkVaV9GW4dqWn47FNz6xLBQ"
                            "/https/steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/fe"
                            "/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg")
                else:
                    embed.set_thumbnail(url=member.avatar_url)

                embed.add_field(name='Joined ' + str(member.guild) + ' on', value=(now[:16]), inline=False)
                embed.add_field(name='Account Created on',
                                value=(str(time[:16]) + "\n" + days.split(",")[0] + " ago"),
                                inline=False)
                embed.set_footer(text="Bhartiya",
                                 icon_url="https://cdn.discordapp.com/icons/226611621059887104"
                                          "/c11623908b1fe534e4d129b7856848ad.webp")
                txt_msg = "Welcome " + member.mention + " to " + str(member.guild)

                if str(member.guild) == self.server:
                    txt_msg += ". Please read #welcome and Enjoy your stay."
                    # noinspection PyBroadException
                    try:
                        role_ass = discord.utils.get(member.guild.roles, name="Members")
                        await member.add_roles(role_ass)
                    except:
                        pass

                else:
                    txt_msg += ". Enjoy your stay."

                await gen.send(txt_msg)
                await gen.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        compare = (str(datetime.date.today()).split("-"), str(member.joined_at).split(" ")[0].split("-"))
        days = str(
            datetime.date(int(compare[0][0]), int(compare[0][1]), int(compare[0][2])) -
            datetime.date(int(compare[1][0]), int(compare[1][1]), int(compare[1][2])))
        for gen in member.guild.channels:
            if "general" == str(gen):
                now = datetime.datetime.now()
                embed = discord.Embed(title=("(" + str(member.id) + ")"), description="\u200b", color=0xff0000)
                embed.set_author(name=member.display_name + " has left " + str(member.guild), url="")

                if member.avatar_url == "":
                    embed.set_thumbnail(
                        url="https://images-ext-1.discordapp.net/external/AsXVksCERNjwXR5gnT-oTkVaV9GW4dqWn47FNz6xLBQ"
                            "/https/steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/fe"
                            "/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg")
                else:
                    embed.set_thumbnail(url=member.avatar_url)

                embed.add_field(name='Left ' + str(member.guild) + ' on', value=(
                    str(now.strftime("%Y-%m-%d %H:%M") + "\nBeen Member for \n" + days.split(",")[0])),
                                inline=False)
                embed.set_footer(text="Bhartiya",
                                 icon_url="https://cdn.discordapp.com/icons/226611621059887104"
                                          "/c11623908b1fe534e4d129b7856848ad.webp")
                await gen.send(embed=embed)
