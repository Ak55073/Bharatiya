from typing import Literal

from discord.ext import commands
from .db_driver import MemberManagerDatabase, ServerData
import discord
from datetime import datetime, timezone
from . import data_structures as models


class MemberManagerCog(commands.Cog):
    def __init__(self, bot, env_var, connection, cursor):
        self.bot = bot
        self.env_var = env_var
        self.db_driver = MemberManagerDatabase(connection, cursor)

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

    async def member_notification(self, member: discord.Member, notify_data: ServerData,
                                  mode: Literal["join", "leave"], ctx=None):
        """
        Send notification when member join/leave server
        :param member: discord-member object -> Member who is leaving/joining
        :param notify_data: MemberData -> server data in member_manage table
        :param mode: "join" / "leave" -> member is joining or leaving
        :param ctx: If the function is triggerd from an interaction,
                    then pass interaction context as ctx,
                    so the bot can reply to interaction command and send private reply to user
        :return: None
        """

        # Creating discord embed message object
        embed = discord.Embed(title=str(member.id), description="\u200b",
                              color=discord.Color.green() if mode == "join" else discord.Color.red())

        if mode == "join":
            # Age of user account = Date_Today - Date_Account Created
            days_count = datetime.now(timezone.utc) - member.created_at  # Account Age
        else:
            # How long user was member of this server = Day_Today - Date_Joined_Server
            days_count = datetime.now(timezone.utc) - member.joined_at  # Membership Age
        date_format = "%d %b, %Y at %I:%M %p %Z"

        txt_msg: str | None = None  # Message is sent along with embed message -> only joining message.
        if mode == "join":  # Member joining server.
            embed.set_author(name=f"{member.display_name} has joined {member.guild.name}", url="")

            embed.add_field(name=f"Joined {member.guild.name} on:",
                            value=datetime.now().strftime(date_format), inline=False)
            embed.add_field(name='Account Created:',
                            value=f"{days_count.days} days ago", inline=False)

            txt_msg = f"Welcome {member.mention} to {member.guild.name}. "
            if notify_data.message:
                # User has provided custom message
                txt_msg += notify_data.message
            else:
                txt_msg += "Enjoy your stay."

            # User has provided a role to be assigned on join
            if notify_data.role_id:
                role_assign = member.guild.get_role(notify_data.role_id)
                if role_assign:
                    await member.add_roles(role_assign)
                else:
                    # Role has been deleted from server. Removing it from database.
                    self.db_driver.update_role(server_id=ctx.guild.id)

        else:  # Member leaving server.
            embed.set_author(name=f"{member.display_name} has left {member.guild.name}", url="")
            embed.add_field(name=f'Left {member.guild.name} on:',
                            value=datetime.now().strftime(date_format), inline=False)
            embed.add_field(name='Been Member for:', value=f"{str(days_count.days)} days", inline=False)

        if member.avatar == "":
            # Member doesn't have a profile photo
            embed.set_thumbnail(url="https://archive.org/download/discordprofilepictures/discordblue.png")
        else:
            embed.set_thumbnail(url=member.avatar)

        embed.set_footer(
            text="Bhartiya",
            icon_url="https://cdn.discordapp.com/avatars/429945357808697355/1610303189d607b5665cba3d037226b7.webp"
        )

        if ctx:  # Replying to an interaction
            await ctx.send(txt_msg, embed=embed, ephemeral=True)
        else:  # Sending notification
            channel = member.guild.get_channel(notify_data.channel_id)
            if channel is None:
                # Channel has been deleted, removing this feature from server
                self.db_driver.delete_server(member.guild.id)
            else:
                await channel.send(txt_msg, embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        notify_data = self.db_driver.fetch_server(member.guild.id)
        if notify_data and notify_data.enable:
            await self.member_notification(member, notify_data, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        notify_data = self.db_driver.fetch_server(member.guild.id)
        if notify_data and notify_data.enable:
            await self.member_notification(member, notify_data, "leave")

    @commands.hybrid_command(name="member-manager-help", description="Help regarding member notification feature.")
    async def mm_help(self, ctx):
        embed = discord.Embed(
            title="Member Notification feature",
            description="Send a notification when a member joins or leaves this server.",
            color=discord.Color.gold()
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name='Message Channel',
            value="A valid channel must be selected, where the notification will be sent.",
            inline=False
        )

        embed.add_field(
            name='Assign Role - OPTIONAL',
            value="Bhartiya can also assign a selected role to the new user when they join this server."
                  "Leave empty to not assign any role on join.",
            inline=False
        )

        embed.add_field(
            name='Custom Message - OPTIONAL',
            value="Users can also add a custom message to be sent along with the joining message."
                  "Leave empty to use default. Default Message: Enjoy your stay.",
            inline=False
        )

        embed.set_footer(
            text="Bhartiya",
            icon_url="https://cdn.discordapp.com/avatars/429945357808697355/1610303189d607b5665cba3d037226b7.webp"
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(name='/member-manager-create', value="Set-up notification feature.", inline=False)
        embed.add_field(name='/member-manager-details', value="Details about notification feature.", inline=False)
        embed.add_field(name='/member-manager-sample', value="Trigger a sample notification message.", inline=False)
        embed.add_field(name='/member-manager-disable', value="Disable notification feature.", inline=False)
        embed.add_field(name='/member-manager-enable', value="Enable notification feature.", inline=False)
        embed.add_field(
            name='/member-manager-update_channel',
            value="Update channel where the notifications will be sent.",
            inline=False
        )
        embed.add_field(
            name='/member-manager-update_message',
            value="Update custom message to be sent along with the joining message.",
            inline=False
        )
        embed.add_field(
            name='/member-manager-update_role',
            value="Change selected role which is assigned to new user.",
            inline=False
        )

        embed.add_field(name='', value="", inline=False)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="member-manager-create", description="Set-up member join/leave notifications.")
    @commands.has_permissions(administrator=True)
    async def create(self, ctx, *, data: models.MemberModel):
        db_data = self.db_driver.fetch_server(ctx.guild.id)
        if db_data:
            await ctx.send("Member manager is already activated. User /member-manager-detail for more info.")
        else:
            self.db_driver.insert_server(server_id=ctx.guild.id, channel_id=data.channel_id.id,
                                         role_id=data.role_id.id, message=data.message, enable=True)
            await ctx.send("Member join/leave notification has been activated.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-detail", description="Details about member notification")
    async def detail(self, ctx):
        # TODO: Delete data on remove
        notify_data = self.db_driver.fetch_server(ctx.guild.id)
        if not notify_data:
            embed = discord.Embed(
                title="MEMBER MANAGER",
                description="DISABLED. To Set-up member notification use /member-manager-create.",
                color=0xff0000
            )

            embed.add_field(
                name='HELP',
                value="Use /member-manager-help for more information.",
                inline=False
            )

            await ctx.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Member Notifications",
            description="Send notification when member join or leave server",
            color=discord.Color.gold()
        )

        embed.add_field(name='', value="", inline=False)

        embed.add_field(
            name='Enabled',
            value=notify_data.enable,
            inline=False
        )

        embed.add_field(
            name='Message Channel:',
            value=f"<#{notify_data.channel_id}>",
            inline=True
        )

        embed.add_field(
            name='Assign Role:',
            value=f"<@&{notify_data.role_id}>" if notify_data.role_id else "None",
            inline=True
        )

        embed.add_field(
            name='Custom Message',
            value=notify_data.message,
            inline=False
        )

        if notify_data.enable:
            embed.set_footer(text="Use '/member-manager-sample' to receive a sample message.")
        else:
            embed.set_footer(text="Use '/member-manager-enable' to enable member notifications feature.")

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="member-manager-sample", description="Trigger a sample notification message")
    async def sample(self, ctx, status: Literal["join", "leave"]):
        """
        Manually trigger join / leave notification
        """
        notify_data = self.db_driver.fetch_server(ctx.guild.id)
        if notify_data and notify_data.enable:
            await self.member_notification(ctx.author, notify_data, status, ctx=ctx)
        else:
            await ctx.send("Member notification feature isn't active.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-enable", description="Activate member notifications.")
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx):
        self.db_driver.update_enable(server_id=ctx.guild.id, enable=True)
        await ctx.send("Member notification have been activated.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-disable", description="Deactivate member notifications.")
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        self.db_driver.update_enable(server_id=ctx.guild.id, enable=False)
        await ctx.send("Member notification have been deactivated.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-update_channel",
                             description="Update channel where the notifications will be sent.")
    @commands.has_permissions(administrator=True)
    async def update_channel(self, ctx, *, data: models.ChannelModel):
        self.db_driver.update_channel(server_id=ctx.guild.id, channel_id=data.channel_id.id)
        await ctx.send(f"Member notification **channel** has been updated to <#{data.channel_id.id}>.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-update_message",
                             description="Update custom message to be sent along with the joining message. "
                                         "Leave empty to use default.")
    @commands.has_permissions(administrator=True)
    async def update_message(self, ctx, *, data: models.MessageModel):
        if data.message:
            self.db_driver.update_message(server_id=ctx.guild.id, message=data.message)
            await ctx.send(f"Member notification **message** has been updated to **{data.message}**.", ephemeral=True)
        else:
            self.db_driver.update_message(server_id=ctx.guild.id)
            await ctx.send("Member notification **message** has been updated to **Enjoy your stay**.", ephemeral=True)

    @commands.hybrid_command(name="member-manager-update_role",
                             description="Change selected role which is assigned to new user. "
                                         "Leave empty to not assign any role on join.")
    @commands.has_permissions(administrator=True)
    async def update_role(self, ctx, *, data: models.RoleModel):
        if data.role_id:
            self.db_driver.update_role(server_id=ctx.guild.id, role_id=data.role_id.id)
            await ctx.send(f"Member will be assigned <@&{data.role_id.id}> on join.", ephemeral=True)
        else:
            self.db_driver.update_role(server_id=ctx.guild.id)
            await ctx.send(f"Member will not be assigned any role on join.", ephemeral=True)

# Delete data on guild remove.
