import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from .Views.SuggestionView import Suggestion


class Commands(commands.Cog):
    def __init__(self, bot, connection, cursor):
        self.bot = bot

    @commands.hybrid_command(description="Everything about this Bhartiya.")
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

        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/"
                                  "216236803710124032/de55f4eac7f02cacd0047013139cd0ae.webp")
        await ctx.send("Suggestions are always welcomed. Use /suggestion to send suggestions.",
                       embed=embed,
                       ephemeral=True)
        await ctx.invoke(self.bot.get_command('role-manager-detail'))
        await ctx.invoke(self.bot.get_command('member-manager-detail'))

    @commands.hybrid_command(description="Change bot playing status.")
    @commands.is_owner()
    async def change(self, ctx, status: str):
        await self.bot.change_presence(activity=discord.Game(name=status))
        await ctx.send(f"Status changed to {status}", ephemeral=True)

    @change.error
    async def change_error(self, ctx, error):
        await ctx.send(f"Only bot owner can use this command.", ephemeral=True, delete_after=10)

    @commands.hybrid_command(description="Tell us, how we can improve?")
    async def suggestion(self, ctx):
        await ctx.interaction.response.send_modal(Suggestion(self.bot))

    @commands.command(pass_context=True)
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, number):
        number = int(number) + 1
        counter = 0
        if number > 102:
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
