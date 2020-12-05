import os
from json import loads

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions, CommandInvokeError

from Driver.dbdriver import DBManage


class MaintainDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            data = loads(open("config.json", "r").read())
            self.DatabaseHelper = DBManage(url=data["MONGO"])
        except FileNotFoundError:
            self.DatabaseHelper = DBManage(url=os.getenv("MONGO"))

    @commands.Cog.listener()
    async def on_ready(self):
        # Validating Database
        await self.bot.change_presence(activity=discord.Game(name='Starting...'))
        await self.DatabaseHelper.startup(self.bot)

        # Running Bot
        await self.bot.change_presence(activity=discord.Game(name='Use >help'))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Adding guild to Database
        self.DatabaseHelper.server_join(guild)

        embed = discord.Embed(title="Bhartiya has joined " + str(guild.name), description="\u200b", color=0x00ff00)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/429945357808697355"
                "/1610303189d607b5665cba3d037226b7.webp?size=128")
        embed.add_field(name='>help',
                        value="Provide general information about bot and server.",
                        inline=False)
        embed.add_field(name='List of command for Bhartiya can be found here:',
                        value="https://github.com/Ak55073/Bharatiya/wiki",
                        inline=False)
        embed.add_field(name='Official bot repo',
                        value="https://github.com/Ak55073/Bharatiya",
                        inline=False)
        embed.set_footer(text="Bhartiya",
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")

        for channel in guild.channels:
            if "general" == str(channel):
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.DatabaseHelper.server_delete_data(guild.id)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        # Changing guild name stored in Database
        if before.name != after.name:
            self.DatabaseHelper.server_update_name(after)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Auto assign role if playing status match any role name in server
        if not after.bot and \
                after.activity is not None and \
                before.activity != after.activity and \
                str(after.activity.type) == "ActivityType.playing":
            auto_role = self.DatabaseHelper.server_query_data(after.guild.id, "auto_role")
            if auto_role:
                for role in after.guild.roles:
                    if after.activity.name.lower() == role.name.lower():
                        role_assign = discord.utils.get(after.guild.roles, name=role.name)
                        await after.add_roles(role_assign)

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def auto_role(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "Do you wish to enable auto_assign?```cs\n" \
                  "-> Bharatiya will automatically assign the role to" \
                  " the user based on their gaming activity in discord.\n" \
                  "-> Name of the role must match(not case-sensitive) the user's playing status to assign the role.\n" \
                  "-> If the server has a 'Cyberpunk' role and user playing status" \
                  " display 'Cyberpunk 2077' then the role will not be assigned.```\n" \
                  "(Y:Yes | N:NO)"
        await ctx.send(message)

        auto_role = await self.bot.wait_for('message', check=check, timeout=60)
        if auto_role.content.lower() in ["y", "yes"]:
            self.DatabaseHelper.server_update_auto_role(
                guild_id=ctx.guild.id,
                enable=True)
            await ctx.send("Auto-role enabled.")
        elif auto_role.content.lower() in ["n", "no"]:
            self.DatabaseHelper.server_update_auto_role(
                guild_id=ctx.guild.id,
                enable=False)
            await ctx.send("Auto-role deactivated.")
        else:
            await ctx.send("Invalid input.")

    @auto_role.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("To prevent spam. Only administrator can use this command.")
        elif isinstance(error, CommandInvokeError):
            await ctx.send("Did not receive any reply from user. Exiting config prompt.")


def setup(bot):
    bot.add_cog(MaintainDB(bot))
