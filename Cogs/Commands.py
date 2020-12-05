import os
from json import loads

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions

from Driver.dbdriver import DBManage


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            data = loads(open("config.json", "r").read())
            self.DatabaseHelper = DBManage(url=data["MONGO"])
        except FileNotFoundError:
            self.DatabaseHelper = DBManage(url=os.getenv("MONGO"))

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="A General purpose open source bot", description="\u200b",
                              color=0xcc0099)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad.webp")

        embed.add_field(name='List of command for Bhartiya can be found here:',
                        value="https://github.com/Ak55073/Bharatiya/wiki",
                        inline=False)
        embed.add_field(name='Official bot repo',
                        value="https://github.com/Ak55073/Bharatiya",
                        inline=False)

        # Checking which modules are enabled
        server_data = self.DatabaseHelper.server_query_data(ctx.guild.id, mode="help")
        if server_data["auto_role"]:
            embed.add_field(name='Role Auto Assign: Enable',
                            value="Use >auto_role to disable.",
                            inline=False)
        else:
            embed.add_field(name='Role Auto Assign: Disable',
                            value="Use >auto_role to enable.",
                            inline=False)

        if server_data["twitch_notification"]["enable"]:
            embed.add_field(name='Twitch Notification: Enable',
                            value="Use >help_twitch for more information.",
                            inline=False)
        else:
            embed.add_field(name='Twitch Notification: Disable',
                            value="Use >help_twitch for more information.",
                            inline=False)

        if server_data["new_member_notification"]["enable"]:
            embed.add_field(name='New Member Notification: Enable',
                            value="Use >help_member_welcome for more information.",
                            inline=False)
        else:
            embed.add_field(name='New Member Notification: Disable',
                            value="Use >help_member_welcome for more information.",
                            inline=False)

        if server_data["self_assign"]["enable"]:
            embed.add_field(name='Self Assign Role: Enable',
                            value="Use >help_self_assign for more information.",
                            inline=False)
        else:
            embed.add_field(name='Self Assign Role: Disable',
                            value="Use >help_self_assign for more information.",
                            inline=False)

        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/"
                                  "216236803710124032/287ada789e1944a72a2f826e229cba29.webp")
        await ctx.send(embed=embed)
        await ctx.send("Suggestions are always welcomed, Use **>suggest_bot <message>** to send suggestions.")

    @commands.command()
    async def change(self, ctx):
        if str(ctx.author.id) == str(self.bot.owner_id):
            await self.bot.change_presence(activity=discord.Game(name=ctx.message.content[8:]))

    @commands.command()
    async def suggest_bot(self, ctx):
        message = ctx.message.content[12:] + "\n\nThis Message was sent by:\n **" + str(ctx.message.author) + "**"
        owner = await self.bot.fetch_user(str(self.bot.owner_id))
        await owner.send(message)
        await ctx.send("Your feedback has been received successfully.")

    @commands.command(pass_context=True)
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, number):
        number = int(number) + 1
        counter = 0
        if number > 101:
            await ctx.send("Limit should not more then 100")
            return

        async for x in ctx.message.channel.history(limit=number):
            if counter < number:
                await x.delete()
                counter += 1

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("To prevent data loss. Only user with manage_messages permission can use clear command.")


def setup(bot):
    bot.add_cog(Commands(bot))
