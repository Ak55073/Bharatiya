import sqlite3

from discord.ext import commands
import discord
from .db_driver import RoleManagerDatabase
from .Views.RoleAssignView import RoleViewAssign
from .Views.ConfirmationView import ConfirmationView
from . import data_structures as models
import re


class RoleManagerCog(commands.Cog):
    def __init__(self, bot, env_var, connection, cursor):
        self.bot = bot
        self.env_var = env_var
        self.db_driver = RoleManagerDatabase(connection, cursor)
        self.role_assign_view = RoleViewAssign(self, self.db_driver)

    async def cog_load(self) -> None:
        self.bot.add_view(RoleViewAssign(self, self.db_driver))
        server_data = self.db_driver.fetch_all_meta()
        for data in server_data:
            if data.enabled:
                await self.refresh_server_silent(server_data=data)

    @staticmethod
    async def valid_color(text: str) -> bool:
        return bool(re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', text))

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"An error occurred: {error}", ephemeral=True)
        elif isinstance(error, discord.errors.NotFound):
            await ctx.send(f"Something went wrong! Please try again. Make sure used command is valid.", ephemeral=True)
        else:
            if self.env_var["DM_OWNER"]:
                owner = await self.bot.fetch_user(str(self.bot.owner_id))
                await owner.send(f'Error occurred in {ctx.cog.__cog_name__}:\n{error}')
                await ctx.send("An unexpected error occurred. Please try again later.", ephemeral=True)
            raise error

    async def send_role_view(self, role_data: models.RoleModel, target_channel):
        embed = discord.Embed(
            title=role_data.name,
            description=str(role_data.role_id),
            color=int(str(role_data.color)[1:], 16)
        )
        await target_channel.send(embed=embed, view=self.role_assign_view)

    async def get_target_roles(self, guild: discord.Guild, color: str) -> dict[int, models.RoleModel]:
        target_roles: dict[int, models.RoleModel] = dict()

        special_roles = self.db_driver.fetch_roles_set(guild.id)
        for role in guild.roles:
            role_id = int(role.id)
            if str(role.colour) == color or role_id in special_roles:
                target_roles[role_id] = models.RoleModel(role_id, role.name, str(role.color))

        return target_roles

    async def refresh_server_process(self, server_data: models.RMServersModel | None = None) -> bool:
        target_guild = self.bot.get_guild(server_data.server_id)
        target_roles: dict[int, models.RoleModel] = await self.get_target_roles(target_guild, color=server_data.color)
        target_channel = target_guild.get_channel(server_data.channel_id)

        if target_channel is None:
            return False

        async for message in target_channel.history():
            if message.author != self.bot.user:
                continue
            else:
                try:
                    if int(message.embeds[0].description) not in target_roles.keys():
                        await message.delete()
                        continue

                    curr_role = int(message.embeds[0].description)

                    if target_roles[curr_role].name != message.embeds[0].title:
                        message.embeds[0].title = target_roles[curr_role].name
                        await message.edit(embed=message.embeds[0])

                    if target_roles[curr_role].color != str(message.embeds[0].color):
                        await message.delete()
                        continue

                    del target_roles[curr_role]
                except ValueError:
                    continue
                except IndexError:
                    continue
                except Exception:
                    raise Exception

        for role_data in target_roles.values():
            await self.send_role_view(role_data, target_channel)
        return True

    async def refresh_server_silent(self, server_id: int = None, server_data: models.RMServersModel | None = None):
        if server_data is None:
            server_data = self.db_driver.fetch_one_meta(server_id)
            if server_data is None:
                return

        if not server_data.enabled:
            return

        if await self.refresh_server_process(server_data):
            return

        # Error occurred. Disabling self assign
        self.db_driver.update_meta_channel(server_id)

    async def refresh_server(self, ctx, server_id: int, server_data: models.RMServersModel | None = None):
        if server_data is None:
            server_data = self.db_driver.fetch_one_meta(server_id)
            if server_data is None:
                return

        if not server_data.enabled:
            return

        if await self.refresh_server_process(server_data):
            return

        # Error occurred. Disabling self assign
        self.db_driver.update_meta_channel(server_id)
        await ctx.send("Error occurred with self assign. Make sure selected channel does not contain any messages. "
                       "Use '/role-manager-set-channel' to activate self assign.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Auto assign role if playing status of a user
         matches any role name in server"""

        # Does not assign roles to bot account
        if after.bot:
            return

        # If playing activity is None
        # Return
        if after.activity is None:
            return

        # User is playing a game
        if str(after.activity.type) != "ActivityType.playing":
            return

        # Server has role-manager feature enabled
        server_data = self.db_driver.fetch_one_meta(after.guild.id)
        if not server_data or not server_data.enabled:
            return

        role_ob = await discord.utils.get(after.guild.roles, name=after.activity.name.lower())
        if role_ob is None:
            return

        if role_ob.color == server_data.color or role_ob.id in self.db_driver.fetch_roles_set(after.guild.id):
            await after.add_roles(role_ob)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        server_data = self.db_driver.fetch_one_meta(role.guild.id)
        if server_data and server_data.enabled and role.colour == server_data.color:
            await self.refresh_server_silent(server_id=role.guild.id)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        server_data = self.db_driver.fetch_one_meta(role.guild.id)
        if not server_data or not server_data.enabled:
            return

        target_roles = self.db_driver.fetch_roles_set(role.guild.id)
        if role.id in target_roles or role.colour == server_data.color:
            await self.refresh_server_silent(server_id=role.guild.id)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        # If true we don't need to update anything
        if before.name == after.name and before.color == after.color:
            return

        await self.refresh_server_silent(server_id=after.guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        server_data = self.db_driver.fetch_one_meta(channel.guild.id)
        if server_data and channel.id == server_data.channel_id:
            self.db_driver.update_meta_channel(channel.guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.db_driver.delete_record(guild.id)

    @commands.hybrid_command(name="role-manager-help", description="How to use role manager?")
    async def help(self, ctx):
        embed = discord.Embed(
            title="ROLE MANAGER",
            description="",
            color=0x00ff00
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name='Bharatiya will automatically assign roles to the user based on their gaming activity in discord.',
            value="Only roles with selected color or special roles will be assigned to the user.",
            inline=False
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(value='',
                        name="By default, Bhartiya uses color #607d8b to identify roles. "
                             "#607d8b is exact same color as discord color palette (first row - last column) color. "
                             "Any role with this color will be managed by role-manager.",
                        inline=False)

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name="Roles can also be manually assigned by clicking ✅ to get the role "
                 "or ❎ remove the role using self assign feature.",
            value="To use self assign, provide a valid channel using /role-manager-set-channel.",
            inline=False
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name="Special Roles",
            value="Special roles can have any color and can be added to the list manually. Using /role-manager-add.",
            inline=False
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name="Getting Started",
            value="Use /role-manager-create to set-up role manager. "
                  "Require a valid hex color code as #XXXXXX (with leading hash) to work. "
                  "Specified color will be used by the role manager to manage roles. Default=#607d8b.",
            inline=False
        )

        embed.add_field(
            name="Detail",
            value="Use /role-manager-detail to check current detail of role manager in this server.",
            inline=False
        )

        embed.set_footer(
            text="Bhartiya",
            icon_url="https://cdn.discordapp.com/avatars/429945357808697355"
                     "/1610303189d607b5665cba3d037226b7.webp?size=128"
        )

        embed.add_field(
            name="Self Assign",
            value="To use self assign, provide a valid channel using /role-manager-set-channel.",
            inline=False
        )

        embed.add_field(
            name="Update Selected Color",
            value="Use /role-manager-color to update selected color. Default=#607d8b",
            inline=False
        )

        embed.add_field(
            name="Special Role",
            value="Use role-manager-add-role or /role-manager-remove-role to "
                  "add or remove special role from role manager.",
            inline=False
        )

        embed.add_field(
            name="Enable/Disable",
            value="Use role-manager-enable or role-manager-disable to "
                  "to temporary enable / disable role manager features..",
            inline=False
        )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="role-manager-create", description="Set-up role manager. "
                                                                     "Use /role-manager-help for more info.")
    @commands.has_permissions(administrator=True)
    async def create(self, ctx, *, data: models.RMColorModel):
        if not (await self.valid_color(data.color)):
            await ctx.send("Invalid color code! Provide a valid HEX Color Code as #XXXXXX", ephemeral=True)
            return

        server_data = self.db_driver.fetch_one_meta(ctx.guild.id)
        if server_data:
            await ctx.send("Role Manager is already activated. Use /role-manager-detail for more info.", ephemeral=True)
        else:
            self.db_driver.insert_meta(server_id=ctx.guild.id, color=data.color)
            await self.refresh_server_silent(server_id=ctx.guild.id)
            await ctx.send("Role Manager has activated successfully. "
                           "Use /role-manager-set-channel to enable self assign.", ephemeral=True)

    @commands.hybrid_command(name="role-manager-detail", description="Details regarding role manager.")
    async def detail(self, ctx):
        server_data = self.db_driver.fetch_one_meta(server_id=ctx.guild.id)
        if not server_data:
            embed = discord.Embed(
                title="ROLE MANAGER",
                description="DISABLED. To Set-up role manager use /role-manager-create",
                color=0xff0000

            )
            embed.add_field(
                name='HELP',
                value="Use /role-manager-help for more information.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="ROLE MANAGER",
                description="Details regarding role manager.",
                color=int(server_data.color[1:], 16)
            )

            embed.add_field(name='', value="", inline=False)

            embed.add_field(
                name='Enabled',
                value=bool(server_data.enabled),
                inline=True
            )

            embed.add_field(
                name='Color',
                value=server_data.color,
                inline=True
            )

            embed.add_field(name='', value="", inline=False)

            if server_data.channel_id:
                embed.add_field(
                    name='Self Assign',
                    value="Enabled" if bool(server_data.enabled) else "Disabled",
                    inline=True
                )

                embed.add_field(
                    name='Channel',
                    value=self.bot.get_channel(int(server_data.channel_id)),
                    inline=True
                )
            else:
                embed.add_field(
                    name='Self Assign',
                    value="Disabled",
                    inline=True
                )

            embed.add_field(name='', value="", inline=False)

            embed.add_field(
                name="Special Roles",
                value="",
                inline=False
            )

            for role_id in self.db_driver.fetch_roles_set(ctx.guild.id):
                embed.add_field(
                    name="",
                    value="<@&" + str(role_id) + ">",
                    inline=True
                )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="role-manager-set-channel", description="Set self assign channel. "
                                                                          "Use /role-manager-help for more info.")
    @commands.has_permissions(administrator=True)
    async def update_self_assign_channel(self, ctx, *, data: models.RMChannelModel):
        server_data = self.db_driver.fetch_one_meta(ctx.guild.id)
        if not server_data or not server_data.enabled:
            await ctx.send(f"Command unavailable. Role Manager is not activated in this server.", ephemeral=True)
            return

        channel_id = data.channel.id if data.channel else None
        prev_channel = server_data.channel_id

        if prev_channel == channel_id:
            await ctx.send(f"New channel is same as old channel.", ephemeral=True)
            return

        if prev_channel:
            confirm = ConfirmationView(confirm="Previous channel cleared.", cancel="Skipped.")
            await ctx.send("Do you wish to delete messages in previous channel? (This will delete **all messages**"
                           " from <#"+str(prev_channel)+">.)", view=confirm, ephemeral=True)

            await confirm.wait()
            if confirm.value is None:
                pass
            elif not confirm.value:
                pass
            else:
                target_channel = ctx.guild.get_channel(prev_channel)
                if target_channel:
                    await target_channel.purge()

        if channel_id:
            await ctx.send(f"Self assign channel switched to <#{channel_id}>", ephemeral=True)
            self.db_driver.update_meta_channel(ctx.guild.id, channel_id)
            await self.refresh_server(ctx, ctx.guild.id)
        else:
            await ctx.send(f"Self assign has been removed from the server.", ephemeral=True)
            self.db_driver.update_meta_channel(ctx.guild.id, channel_id)
            await self.refresh_server_silent(ctx.guild.id)

    @commands.hybrid_command(name="role-manager-color", description="Set role manager color. "
                                                                    "Use /role-manager-help for more info.")
    @commands.has_permissions(administrator=True)
    async def update_self_assign_color(self, ctx, *, data: models.RMColorModel):
        if not await self.valid_color(data.color):
            await ctx.send("Invalid color code! Provide a valid HEX Color Code as #XXXXXX", ephemeral=True)
            return

        server_data = self.db_driver.fetch_one_meta(ctx.guild.id)
        if server_data and server_data.enabled:
            self.db_driver.update_meta_color(ctx.guild.id, data.color)
            await ctx.send(f"Role manager color changed successfully.", ephemeral=True)
            if server_data.channel_id:
                target_channel = ctx.guild.get_channel(server_data.channel_id)
                if not target_channel:
                    self.db_driver.update_meta_channel(ctx.guild.id, channel_id=None)
                else:
                    await self.refresh_server_silent(ctx.guild.id)
        else:
            await ctx.send(f"Command unavailable. Role Manager is not activated in this server.", ephemeral=True)

    async def switch_enable(self, ctx, enable):
        server_data = self.db_driver.fetch_one_meta(server_id=ctx.guild.id)
        if not server_data:
            message = "Set-up auto assign before using this command. Use '/role-manager create'"
        else:
            if server_data.enabled == enable:
                message = f"Auto Role is already {'enabled' if enable else 'disabled'} in this server.\n"
            else:
                message = f"Auto Role has been {'enabled' if enable else 'disabled'}.\n"
                self.db_driver.update_meta_enable(ctx.guild.id, enable=bool(enable))
        await ctx.send(message, ephemeral=True)

    @commands.hybrid_command(name="role-manager-enable", description="Enable role manager features.")
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx):
        await self.switch_enable(ctx, 1)
        await self.refresh_server_silent(ctx.guild.id)

    @commands.hybrid_command(name="role-manager-disable", description="Disable role manager features.")
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        await self.switch_enable(ctx, 0)

    @commands.hybrid_command(name="role-manager-add-role", description="Add a special role.")
    @commands.has_permissions(administrator=True)
    async def add_role(self, ctx, *, data: models.SpecialRoleData):
        if not data.role.is_assignable():
            await ctx.send(f"**Failed**. Bhartiya doesn't have permission to manage <@&{data.role.id}>", ephemeral=True)
            return

        try:
            self.db_driver.insert_role(ctx.guild.id, data.role.id)
            message = f"<@&{data.role.id}> added to self assign."
            await ctx.send(message, ephemeral=True)
            await self.refresh_server_silent(ctx.guild.id)
        except sqlite3.IntegrityError:
            message = f"<@&{data.role.id}> is already added to special role list."
            await ctx.send(message, ephemeral=True)

    @commands.hybrid_command(name="role-manager-remove-role", description="Remove a special role.")
    @commands.has_permissions(administrator=True)
    async def remove_role(self, ctx, *, data: models.SpecialRoleData):
        row = self.db_driver.delete_role(role_id=data.role.id)
        if row:
            message = f"<@&{data.role.id}> deleted from self assign."
            await ctx.send(message, ephemeral=True)
            await self.refresh_server_silent(ctx.guild.id)
        else:
            message = f"<@&{data.role.id}> doesn't exist in self assign."
            await ctx.send(message, ephemeral=True)

    @commands.hybrid_command(name="role-manager-refresh", description="Add special role.")
    @commands.has_permissions(administrator=True)
    async def refresh(self, ctx):
        await ctx.send("Refresh Started.", ephemeral=True)
        await self.refresh_server(ctx, server_id=ctx.guild.id)
        await ctx.send("Refresh successful.", ephemeral=True)

    @commands.hybrid_command(name="role-manager-refresh_all", description="Add special role.")
    @commands.is_owner()
    async def refresh_all(self, ctx):
        server_data = self.db_driver.fetch_all_meta()
        for data in server_data:
            await self.refresh_server(ctx, server_id=data.server_id, server_data=data)
        await ctx.send("Refresh successful.", ephemeral=True)
