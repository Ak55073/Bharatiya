import discord
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot, owner, server_id):
        self.bot = bot
        self.owner = owner
        self.server_id = server_id

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="A Private bot created for server Bhartiya.", description="\u200b", color=0xcc0099)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad"
                                  ".webp")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad.webp")

        embed.add_field(name='>clear <limit>', value="Delete <limit> number of messages from the channel.", inline=False)
        embed.add_field(name='>subot <message>', value="Use to send suggestion about this bot.", inline=False)
        embed.add_field(name='>stream <twitch_username>', value="Display detailed information about twitch streamer.",
                        inline=False)

        embed.add_field(name='\u200b', value="Only for admins.", inline=False)
        embed.add_field(name='Join/Leave notification',
                        value="Rename 'general' to 'generals' to disable member join and leave notifications",
                        inline=False)

        if ctx.guild.id == self.server_id:
            embed.add_field(name='Role self assignment',
                            value="Head to #self_assign (Channel) and click '✅' or '❎' to 'get' or 'remove' particular role",
                            inline=False)

        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/216236803710124032/287ada789e1944a72a2f826e229cba29"
                                  ".webp")
        await ctx.send(embed=embed)
        await ctx.send("Suggestions are always welcomed, Use **>subot <message>** to send suggestions.")

    @commands.command()
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

    @commands.command()
    async def change(self, ctx):
        if ctx.message.author.id == self.owner:
            await self.bot.change_presence(activity=discord.Game(name=ctx.message.content[8:]))

    @commands.command()
    async def subot(self, ctx):
        message = ctx.message.content[7:] + "\n\nThis Message was sent by:\n **" + str(ctx.message.author) + "**"
        owner = self.bot.get_user(self.owner)
        await owner.send(message)
        await ctx.send("Your feedback has been received successfully.")
