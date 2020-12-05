import os
import re
from json import loads

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions, CommandInvokeError
from discord.ext.tasks import loop

from Driver.dbdriver import DBManage


class RoleAssign(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            data = loads(open("config.json", "r").read())
            self.DatabaseHelper = DBManage(url=data["MONGO"])
        except FileNotFoundError:
            self.DatabaseHelper = DBManage(url=os.getenv("MONGO"))

    @commands.Cog.listener()
    async def on_ready(self):
        await self.pre_process()
        self.channel_maintenance.start()

    async def pre_process(self):
        # Create a list of role (list_roles) and member member who have them
        self_assign = self.DatabaseHelper.server_query_data(guild_id=None, mode="self_assign_all")
        for data in self_assign:
            guild = self.bot.get_guild(data["id"])
            list_roles = dict()
            for role in guild.roles:
                if str(role.colour) == data["self_assign"]["color"] \
                        or str(role.name) in data["self_assign"]["special_role"]:
                    list_roles[role] = list()
                    if data["self_assign"]["show_members"]:
                        for member in guild.members:
                            if str(role) in [r.name for r in member.roles]:
                                list_roles[role].append(member)

            channel = discord.utils.get(guild.channels, name=data["self_assign"]["channel"])
            await self.update_self_assign(list_roles, channel)

    @staticmethod
    async def update_self_assign(list_roles, channel):
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

    @loop(minutes=30)
    async def channel_maintenance(self):
        await self.check_roles(self.bot, self.DatabaseHelper, ctx=None)

    @commands.command(pass_context=True)
    async def maintain_self_assign(self, ctx):
        await self.check_roles(self.bot, self.DatabaseHelper, ctx=ctx, guild_id=ctx.guild.id)

    async def check_roles(self, bot, DatabaseHelper, ctx, guild_id=None):
        if ctx:
            self_data = DatabaseHelper.server_query_data(ctx.guild.id, mode="self_assign")
            if self_data["enable"]:
                self_data = [
                    {"id": ctx.guild.id, "self_assign": self_data},
                ]
            else:
                await ctx.send("Self assign isn't activated in this server.\n"
                               "use >set_self_assign to activate this feature")
                return
        elif guild_id:
            self_data = DatabaseHelper.server_query_data(guild_id, mode="self_assign")
            self_data = [
                {"id": guild_id, "self_assign": self_data},
            ]
        else:
            self_data = DatabaseHelper.server_query_data(guild_id=None, mode="self_assign_all")

        # TODO: IF continuous error disable show member
        while True:
            error_list, self_data = await self.validate_assign(bot=bot, self_assign=self_data)
            if error_list:
                for server_data in error_list:
                    await self.update_self_assign(server_data[0], server_data[1])
            else:
                if ctx:
                    message = "Check Successful"
                    await ctx.send(message)
                break

    @staticmethod
    async def validate_assign(bot, self_assign):
        e3_list = list()
        temp_self_assign = list()

        for data in self_assign:
            guild = bot.get_guild(data["id"])
            list_roles = dict()
            for role in guild.roles:
                if str(role.colour) == data["self_assign"]["color"] \
                        or str(role.name) in data["self_assign"]["special_role"]:
                    list_roles[role] = list()
                    if data["self_assign"]["show_members"]:
                        for member in guild.members:
                            if str(role) in [r.name for r in member.roles]:
                                list_roles[role].append(member)

            channel = discord.utils.get(guild.channels, name=data["self_assign"]["channel"])
            channel_list_role = list()
            channel_list_member = dict()
            async for x in channel.history():
                role = str(x.content.split("**")[1])
                channel_list_role.append(role)
                if data["self_assign"]["show_members"]:
                    body = list(x.content.split("```")[1].split('\n'))[1:-1]
                    channel_list_member[role] = body

            flag_error = False
            for role in list_roles.keys():
                if str(role) in channel_list_role:
                    channel_list_role.remove(str(role))
                else:
                    e3_list.append([list_roles, channel])
                    temp_self_assign.append(data)
                    flag_error = True
                    break
            else:
                if len(channel_list_role) > 0:
                    e3_list.append([list_roles, channel])
                    temp_self_assign.append(data)
                    flag_error = True

            if not flag_error and data["self_assign"]["show_members"]:
                flag_nested_exit = False
                for role in list_roles.keys():
                    for member in list_roles[role]:
                        if str(member) in channel_list_member[role.name]:
                            channel_list_member[role.name].remove(str(member))
                        else:
                            e3_list.append([list_roles, channel])
                            temp_self_assign.append(data)
                            flag_nested_exit = True
                            break
                    else:
                        if len(channel_list_member[role.name]) > 0:
                            e3_list.append([list_roles, channel])
                            temp_self_assign.append(data)
                            flag_nested_exit = True
                    if flag_nested_exit:
                        break

        return e3_list, temp_self_assign

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return
        self_assign = self.DatabaseHelper.server_query_data(after.guild.id, "self_assign")
        if self_assign["enable"] and self_assign["show_members"]:
            change = list(set(after.roles) ^ set(before.roles))
            if str(change[0].colour) == self_assign["color"] \
                    or str(change[0].name) in self_assign["special_role"]:
                channel = discord.utils.get(after.guild.channels, name=self_assign["channel"])
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
    async def on_reaction_add(self, reaction, user):
        self_assign = self.DatabaseHelper.server_query_data(user.guild.id, "self_assign")
        if self_assign["enable"]:
            if reaction.count > 1 and str(reaction.message.channel) == self_assign["channel"]:
                role_name = discord.utils.get(user.guild.roles, name=str(reaction.message.content).split("**")[1])
                if reaction.emoji == '✅':
                    await user.add_roles(role_name)
                    await reaction.remove(user)

                elif reaction.emoji == '❎':
                    await user.remove_roles(role_name)
                    await reaction.remove(user)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        self_assign = self.DatabaseHelper.server_query_data(role.guild.id, "self_assign")
        if self_assign["enable"] and (str(role.colour) == self_assign["color"]
                                      or role.name in self_assign["special_role"]):
            if str(role.name) in self_assign["special_role"]:
                self_assign["special_role"].remove(role.name)
                self.DatabaseHelper.server_update_self_assign(
                    guild_id=role.guild.id,
                    channel=self_assign["channel"],
                    color=self_assign["color"],
                    role=self_assign["special_role"] if self_assign["special_role"] else None,
                    show_member=self_assign["show_members"])

            channel = discord.utils.get(role.guild.channels, name=self_assign["channel"])
            async for x in channel.history():
                if str(x.content.split("**")[1]) == role.name:
                    await x.delete()
                    break

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        self_assign = self.DatabaseHelper.server_query_data(after.guild.id, "self_assign")
        if self_assign["enable"]:
            if str(after.colour) == self_assign["color"] and str(before.colour) != self_assign["color"]:
                await self.check_roles(self.bot, self.DatabaseHelper, ctx=None, guild_id=after.guild.id)

            elif str(before.colour) == self_assign["color"] and str(after.colour) != self_assign["color"]:
                channel = discord.utils.get(after.guild.channels, name=self_assign["channel"])
                async for x in channel.history():
                    if str(x.content.split("**")[1]) == after.name:
                        await x.delete()
                        break

            elif (str(after.colour) == self_assign["color"] or before.name in self_assign["special_role"]) and (
                    str(before.name) != str(after.name)):
                if str(before.name) in self_assign["special_role"]:
                    self_assign["special_role"][self_assign["special_role"].index(before.name)] = after.name
                    self.DatabaseHelper.server_update_self_assign(
                        guild_id=after.guild.id,
                        channel=self_assign["channel"],
                        color=self_assign["color"],
                        role=self_assign["special_role"] if self_assign["special_role"] else None,
                        show_member=self_assign["show_members"])
                channel = discord.utils.get(after.guild.channels, name=self_assign["channel"])
                async for x in channel.history():
                    if str(x.content.split("**")[1]) == before.name:
                        msg = x.content.split("**")
                        msg[1] = after.name
                        msg = "**".join(msg)
                        await x.edit(content=msg)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        self_assign = self.DatabaseHelper.server_query_data(channel.guild.id, "self_assign")
        if self_assign["enable"] and channel.name == self_assign["channel"]:
            self.DatabaseHelper.server_update_self_assign(
                guild_id=channel.guild.id,
                channel=None,
                color=None,
                role=None,
                show_member=False,
                enable=False)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        self_assign = self.DatabaseHelper.server_query_data(after.guild.id, "self_assign")
        if self_assign["enable"] and before.name != after.name and before.name == self_assign["channel"]:
            self.DatabaseHelper.server_update_self_assign(
                guild_id=after.guild.id,
                channel=after.name,
                color=self_assign["color"],
                role=self_assign["special_role"],
                show_member=self_assign["show_members"])

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        self_assign = self.DatabaseHelper.server_query_data(message.guild.id, "self_assign")
        if self_assign["enable"] and message.channel.name == self_assign["channel"]:
            for emoji in ['✅', '❎']:
                await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        self_assign = self.DatabaseHelper.server_query_data(user.guild.id, "self_assign")
        if self_assign["enable"] and reaction.message.channel.name == self_assign["channel"] \
                and user.name == self.bot.user.name:
            for emoji in ['✅', '❎']:
                await reaction.message.add_reaction(emoji)

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def set_self_assign(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "**Welcome to self assign configuration prompt**.\n" \
                  "> -> Self role assignment allows the user to manually assign a role (to himself/herself) " \
                  "by clicking ✅ to get the role or ❎ remove the role.\n" \
                  "> -> Role color is used to automatically manage the roles.\n " \
                  "> -> Role with selected color will automatically be " \
                  "added and removed from the self-assign channel.\n " \
                  "> -> Special roles can also be added to the list manually. Special roles can have any color. \n\n " \
                  "Specify a **channel** for self assign.```cs\n" \
                  "> Channel must already exist.\n" \
                  "> Do not tag the channel. Enter channel name only.\n" \
                  "> Text is case sensitive.\n" \
                  "Type \"exit\" or \"none\" to cancel prompt.```"
        await ctx.send(message)
        while True:
            channel_name = await self.bot.wait_for('message', check=check, timeout=90)

            if channel_name.content.lower() in ["skip", "none", "exit"]:
                await ctx.send("Self assign can't work without a proper channel. Cancelling prompt..")
                return

            channel_name = discord.utils.get(ctx.guild.text_channels, name=channel_name.content)
            if channel_name:
                break
            else:
                await ctx.send(
                    "**Error 404: Channel does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

        await ctx.send("Confirm **#" + channel_name.name
                       + "** to be used with self assign?\n"
                         "```\n"
                         "> ALL MESSAGES IN THE GIVEN CHANNEL WILL BE DELETED.\n"
                         "> Ensure no one other than bot can message in the given channel.\n"
                         "> Ensure channel is muted as bot will refresh channel often.```"
                         "(Y:Yes|N:NO)")
        prompt = await self.bot.wait_for('message', check=check, timeout=30)
        if prompt.content.lower() not in ["y", "yes"]:
            await ctx.send("Self-assign prompt cancelled.")
            return

        message = "Enter a Hex Color Code to be used as identifier-color.\n" \
                  "All role having the given color will be added to self assign channel```cs\n" \
                  "> Must be hex color code only. Default: #607d8b\n" \
                  "> Text is case sensitive.\n" \
                  "Type \"skip\" or \"none\" to use default color.\n" \
                  "Type \"exit\" to cancel prompt```"
        await ctx.send(message)
        while True:
            color_name = await self.bot.wait_for('message', check=check, timeout=60)
            if color_name.content.lower() in ["skip", "none"]:
                color_name = "#607d8b"
                break
            elif color_name.content.lower() in ["exit"]:
                await ctx.send("Prompt Cancelled.")
                return

            if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_name.content.lower()):
                await ctx.send("Color Saved.")
                color_name = color_name.content.lower()
                break
            else:
                await ctx.send(
                    "Invalid Hex Color code provided..\n"
                    "Try again or type **exit** to cancel.")

        message = " Enter special role to be added in self assign.```cs\n" \
                  "> Special role can have any color.\n" \
                  "> Role must already exist.\n" \
                  "Type \"skip\" or \"none\" to skip special role.\n" \
                  "Type \"exit\" to cancel prompt.```"
        await ctx.send(message)
        role_list = list()
        while True:
            special_role = await self.bot.wait_for('message', check=check, timeout=60)

            if special_role.content.lower() in ["skip", "none"]:
                break
            elif special_role.content.lower() in ["empty"]:
                role_list = []
                message = "Enter another special role to add in self assign.```cs\n" \
                          "> Special role can have any color.\n" \
                          "> Role must already exist.\n" \
                          "> {count} is/are already registered.\n" \
                          "Type \"empty\" to remove current special role.\n" \
                          "Type \"skip\" or \"none\" to continue with already added role.\n" \
                          "Type \"exit\" to cancel prompt.```".format(count=role_list if role_list else "No Role")
                await ctx.send(message)
                continue
            elif special_role.content.lower() in ["exit"]:
                await ctx.send("self-assign prompt cancelled.")
                return

            special_role = discord.utils.get(ctx.guild.roles, name=special_role.content)
            if special_role:
                role_list.append(special_role.name)
                await ctx.send("Do you wish to add another special role?\n(Y:Yes|N:NO)")
                prompt = await self.bot.wait_for('message', check=check, timeout=60)
                if prompt.content.lower() == "n":
                    break
                else:
                    message = "Enter another special role to add in self assign.```cs\n" \
                              "> Special role can have any color.\n" \
                              "> Role must already exist.\n" \
                              "> {count} is/are already registered.\n" \
                              "Type \"empty\" to remove current special role.\n" \
                              "Type \"skip\" or \"none\" to continue with already added role.\n" \
                              "Type \"exit\" to cancel prompt.```".format(count=role_list if role_list else "No Role")
                    await ctx.send(message)
            else:
                await ctx.send(
                    "**Error 404: Role does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

        show_members = False
        if len(ctx.guild.members) > 200:
            await ctx.send("Guild with more than 200 member can not use show member.")
        else:
            await ctx.send("Do you wish to show members list in self assign?\n(Y:Yes|N:NO)")
            prompt = await self.bot.wait_for('message', check=check, timeout=30)
            if prompt.content.lower() in ["y", "yes"]:
                show_members = True

            self.DatabaseHelper.server_update_self_assign(
                guild_id=ctx.guild.id,
                channel=channel_name.name,
                color=color_name,
                role=role_list,
                show_member=show_members)

        self_assign = self.DatabaseHelper.server_query_data(guild_id=ctx.guild.id, mode="self_assign")
        self_assign = [
            {"id": ctx.guild.id, "self_assign": self_assign},
        ]
        for data in self_assign:
            guild = self.bot.get_guild(data["id"])
            list_roles = dict()
            for role in guild.roles:
                if str(role.colour) == data["self_assign"]["color"] \
                        or str(role.name) in data["self_assign"]["special_role"]:
                    list_roles[role] = list()
                    if data["self_assign"]["show_members"]:
                        for member in guild.members:
                            if str(role) in [r.name for r in member.roles]:
                                list_roles[role].append(member)

            channel = discord.utils.get(guild.channels, name=data["self_assign"]["channel"])
            await self.update_self_assign(list_roles, channel)

        await ctx.send("Configuration saved successfully. \nAll future roles with " + color_name +
                       " color will be automatically added and removed to/from #" + channel_name.name +
                       "\nUse >help_self_assign for more information.")
        await self.check_roles(self.bot, self.DatabaseHelper, ctx=None, guild_id=ctx.guild.id)

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def remove_self_assign(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        message = "Do you wish to remove self assign channel?\n(Y:YES|N:NO)"
        await ctx.send(message)
        prompt = await self.bot.wait_for('message', check=check, timeout=30)
        if prompt.content.lower() in ["yes", "y"]:
            self.DatabaseHelper.server_update_self_assign(
                guild_id=ctx.guild.id,
                channel=None,
                color=None,
                role=None,
                show_member=False,
                enable=False)
            await ctx.send("Self assign channel deactivated.")
        else:
            await ctx.send("Prompt canceled.")

    @commands.command(pass_context=True)
    @has_permissions(administrator=True)
    async def special_role(self, ctx):
        def check(msg):
            return msg.author == ctx.message.author

        data = self.DatabaseHelper.server_query_data(ctx.guild.id, "self_assign")

        if not data["enable"]:
            await ctx.send("Self assign not activated. Use set_self_assign to activate self assign,")
            return

        role_list = data["special_role"] if data["special_role"] else []
        while True:
            message = "Enter another special role to add in self assign.```cs\n" \
                      "> Special role can have any color.\n" \
                      "> Role must already exist.\n" \
                      "> {count} is/are already registered.\n" \
                      "Type \"empty\" to remove current special role.\n" \
                      "Type \"skip\" or \"none\" to continue with already added role.\n" \
                      "Type \"exit\" to cancel prompt.```".format(count=role_list if role_list else "No Role")
            await ctx.send(message)

            special_role = await self.bot.wait_for('message', check=check, timeout=60)

            if special_role.content.lower() in ["skip", "none"]:
                break
            elif special_role.content.lower() in ["empty"]:
                role_list = []
                continue
            elif special_role.content.lower() in ["exit"]:
                await ctx.send("self-assign prompt cancelled.")
                return

            special_role = discord.utils.get(ctx.guild.roles, name=special_role.content)
            if special_role:
                role_list.append(special_role.name)
                await ctx.send("Do you wish to add another special role?\n(Y:Yes|N:NO)")
                prompt = await self.bot.wait_for('message', check=check, timeout=60)
                if prompt.content.lower() == "n":
                    break

            else:
                await ctx.send(
                    "**Error 404: Role does not exist** (Text is case-sensitive).\n"
                    "Try again or type **exit** to cancel.")

        self.DatabaseHelper.server_update_self_assign(
            guild_id=ctx.guild.id,
            channel=data["channel"],
            color=data["color"],
            role=role_list if role_list else None,
            show_member=data["show_members"])

        self_assign = self.DatabaseHelper.server_query_data(guild_id=ctx.guild.id, mode="self_assign")
        self_assign = [
            {"id": ctx.guild.id, "self_assign": self_assign},
        ]
        for data in self_assign:
            guild = self.bot.get_guild(data["id"])
            list_roles = dict()
            for role in guild.roles:
                if str(role.colour) == data["self_assign"]["color"] \
                        or str(role.name) in data["self_assign"]["special_role"]:
                    list_roles[role] = list()
                    if data["self_assign"]["show_members"]:
                        for member in guild.members:
                            if str(role) in [r.name for r in member.roles]:
                                list_roles[role].append(member)

            channel = discord.utils.get(guild.channels, name=data["self_assign"]["channel"])
            await self.update_self_assign(list_roles, channel)

        await ctx.send("Configuration saved successfully.\n"
                       "Use >help_self_assign for more information.")
        await self.check_roles(self.bot, self.DatabaseHelper, ctx=None, guild_id=ctx.guild.id)

    @set_self_assign.error
    @remove_self_assign.error
    @special_role.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("To prevent data loss. Only user with administrator permission can use clear command.")
        elif isinstance(error, CommandInvokeError):
            await ctx.send("Did not receive any reply from user. Exiting config prompt.")

    @commands.command(pass_context=True)
    async def help_self_assign(self, ctx):
        self_assign = self.DatabaseHelper.server_query_data(ctx.guild.id, mode="self_assign")
        embed = discord.Embed(title="Self Assign Role", description="\u200b",
                              color=0xcc0099)
        embed.set_author(name='Bhartiya',
                         icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                                  "/1610303189d607b5665cba3d037226b7.webp?size=128")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/226611621059887104/c11623908b1fe534e4d129b7856848ad.webp")

        if self_assign["enable"]:
            embed.add_field(name='Show Members',
                            value=self_assign["show_members"],
                            inline=True)
            embed.add_field(name='Channel',
                            value=self_assign["channel"],
                            inline=True)
            embed.add_field(name='Color',
                            value=self_assign["color"],
                            inline=True)
            embed.add_field(name='Special Role',
                            value=str(self_assign["special_role"])[1:-1],
                            inline=False)
            embed.add_field(name='\u200b',
                            value="Commands",
                            inline=False)
            embed.add_field(name='>set_self_assign',
                            value='Update settings for self assign channel.',
                            inline=False)
            embed.add_field(name='>maintain_self_assign',
                            value='Automatically check and fix error in self assign channel.',
                            inline=False)
            embed.add_field(name='>special_role',
                            value='Add or remove roles from special role list.',
                            inline=False)
            embed.add_field(name='>remove_self_assign',
                            value='Disable self assign channel from this server.',
                            inline=False)
        else:
            embed.add_field(name='Self Assign Role: Disable',
                            value="Use >set_self_assign to enable.",
                            inline=False)
        embed.add_field(name='\u200b', value="Made by:", inline=False)
        embed.set_footer(text="VampireBl00d#2521",
                         icon_url="https://cdn.discordapp.com/avatars/"
                                  "216236803710124032/287ada789e1944a72a2f826e229cba29.webp")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(RoleAssign(bot))
