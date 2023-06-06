from dataclasses import dataclass
from discord.ext import commands
import discord


class RMColorModel(commands.FlagConverter):
    color: str = commands.flag(
        default="#607d8b",
        description='Enter a Hex Color Code to be used as identifier. Leave empty to set default. Default: #607d8b'
    )


class RMChannelModel(commands.FlagConverter):
    channel: discord.TextChannel | None = commands.flag(
        default=None,
        description='Which channel should be used for self assign roles. Default: None'
    )


class AutoAssignData(commands.FlagConverter):
    channel: discord.TextChannel | None = commands.flag(
        default=None,
        description='Which channel should be used for self assign roles. Default: None'
    )
    color: str | None = commands.flag(
        default="#607d8b",
        description='Enter a Hex Color Code to be used as identifier. Default: #607d8b'
    )


class SpecialRoleData(commands.FlagConverter):
    role: discord.Role = commands.flag(
        description='Add special role to auto assign.'
    )


@dataclass
class RoleModel:
    role_id: int
    name: str
    color: str = "#607d8b"


@dataclass
class RMServersModel:
    server_id: int
    channel_id: int
    enabled: int = 1
    color: str = "#607d8b"