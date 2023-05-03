from discord.ext import commands
import discord
from dataclasses import dataclass


# How server data is stored in database
@dataclass()
class ServerData:
    server_id: int
    channel_id: int
    role_id: int | None
    message: str = "Enjoy your stay."
    enable: bool = True


# Input types for discord hybrid commands
# Stores message which is sent along member joining notifications
class MessageModel(commands.FlagConverter):
    message: str = commands.flag(
        default="Enjoy your stay.",
        description='You can also add a custom message to be sent along with the joining message. '
                    'Leave empty to set default.'
    )


# Stores channel where member notifications is sent.
class ChannelModel(commands.FlagConverter):
    channel_id: discord.TextChannel = commands.flag(
        description='A valid channel must be selected, where the notification will be sent.',
    )


# Stores role object which is assigned to user on join
class RoleModel(commands.FlagConverter):
    role_id: discord.Role | None = commands.flag(
        default=None,
        description='Role which is assigned to user when they join this server. Leave empty to not assign any role.'
    )


# Contains all data need to set up notification feature.
class MemberModel(MessageModel, ChannelModel, RoleModel):
    pass
