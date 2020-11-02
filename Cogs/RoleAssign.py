import discord
from discord.ext import commands


class RoleAssign(commands.Cog):
    def __init__(self, bot, owner, server_id, channel_id, identifier_color, special_roles):
        self.bot = bot
        self.owner = owner
        self.guild = server_id
        self.channel = channel_id
        self.identifier_color = identifier_color
        self.special_roles = special_roles

    @commands.Cog.listener()
    async def on_ready(self):
        await self.pre_process()

    async def pre_process(self):
        guild = self.bot.get_guild(self.guild)
        list_roles = dict()
        for role in guild.roles:
            if str(role.colour) == self.identifier_color or str(role.name) in self.special_roles:
                list_roles[role] = list()
                for member in guild.members:
                    for i in member.roles:
                        if i.name == str(role):
                            print(member)
                            list_roles[role].append(member)

        await self.update_channel(list_roles)

    async def update_channel(self, list_roles):
        channel = self.bot.get_channel(self.channel)
        async for x in channel.history():
            await x.delete()

        for role in list_roles.keys():
            if list_roles[role]:
                content = "**" + str(role) + "**```cs\n"
                for member in list_roles[role]:
                    content += str(member) + "\n"
                content += "```"
                msg = await channel.send(content)

            else:
                msg = await channel.send("**" + str(role) + "**```\n```")

            for emoji in ['✅', '❎']:
                await msg.add_reaction(emoji)

        await self.check_roles(None)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        guild = self.bot.get_guild(self.guild)
        channel = self.bot.get_channel(self.channel)
        if reaction.count > 1 and str(reaction.message.guild) == guild.name and str(
                reaction.message.channel) == str(channel.name):
            role_name = discord.utils.get(guild.roles, name=str(reaction.message.content).split("**")[1])
            if reaction.emoji == '✅':
                await user.add_roles(role_name)
                await reaction.remove(user)

            elif reaction.emoji == '❎':
                await user.remove_roles(role_name)
                await reaction.remove(user)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = self.bot.get_guild(self.guild)
        channel = self.bot.get_channel(self.channel)
        if before.roles != after.roles and str(after.guild) == guild.name:
            change = list(set(after.roles) ^ set(before.roles))
            msg = None
            async for x in channel.history():
                if str(x.content.split("**")[1]) == str(change[0].name):
                    msg = x
            head = msg.content.split("```")[0]
            body = list(msg.content.split("```")[1].split('\n'))

            if len(before.roles) > len(after.roles):
                body.pop(body.index(str(after)))
                body.pop()
                if len(body) == 1:
                    content = head + "```\n```"
                else:
                    body = "\n".join(body)
                    content = head + "```" + body + "\n```"
                await msg.edit(content=content)

            else:
                body[len(body) - 1] = str(before)
                body[0] = "cs"
                body = "\n".join(body)
                content = head + "```" + body + "\n```"
                await msg.edit(content=content)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = self.bot.get_guild(self.guild)
        channel = self.bot.get_channel(self.channel)
        if str(role.colour) == self.identifier_color and str(role.guild) == guild.name:
            async for x in channel.history():
                if str(x.content.split("**")[1]) == role.name:
                    await x.delete()
                    break

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = self.bot.get_guild(self.guild)
        channel = self.bot.get_channel(self.channel)
        if str(after.colour) == self.identifier_color and str(before.colour) != self.identifier_color and str(
                after.guild) == guild.name:
            list_roles = list()
            for mem in guild.members:
                for i in mem.roles:
                    if i.name == after.name:
                        list_roles.append(mem)

            if list_roles:
                content = "**" + str(after.name) + "**```cs\n"
                for member in list_roles:
                    content += str(member) + "\n"
                content += "```"
                msg = await channel.send(content)

            else:
                msg = await channel.send("**" + str(after.name) + "**```\n```")

            for emoji in ['✅', '❎']:
                await msg.add_reaction(emoji)

        elif str(before.colour) == self.identifier_color and str(after.colour) != self.identifier_color and str(
                after.guild) == guild.name:
            async for x in channel.history():
                if str(x.content.split("**")[1]) == after.name:
                    await x.delete()
                    break

        if str(after.colour) == self.identifier_color and before.name != after.name and str(
                after.guild) == guild.name:
            async for x in channel.history():
                if str(x.content.split("**")[1]) == before.name:
                    msg = x.content.split("**")
                    msg[1] = after.name
                    msg = "**".join(msg)
                    await x.edit(content=msg)

    @commands.command()
    async def check_roles(self, ctx):
        guild = self.bot.get_guild(self.guild)
        channel = self.bot.get_channel(self.channel)
        if ctx is None or ctx.message.author.id == self.owner:
            list_roles = dict()
            for role in guild.roles:
                if str(role.colour) == self.identifier_color or str(role.name) in self.special_roles:
                    list_roles[role] = list()
                    for member in guild.members:
                        for i in member.roles:
                            if i.name == str(role):
                                list_roles[role].append(member)

            for role in list_roles.keys():
                valid_role = False
                async for x in channel.history():
                    if str(x.content.split("**")[1]) == str(role.name):
                        valid_role = True
                        body = list(x.content.split("```")[1].split('\n'))
                        body = body[1:-1]
                        for mem in list_roles[role]:
                            if str(mem) in body:
                                body.pop(body.index(str(mem)))
                            else:
                                await self.update_channel(list_roles)
                                return
                        if len(body) > 0:
                            await self.update_channel(list_roles)
                            return

                if not valid_role:
                    await self.update_channel(list_roles)
                    return
            if ctx:
                message = "Check Successful"
                owner = self.bot.get_user(self.owner)
                await owner.send(message)
