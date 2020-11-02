import json
import os

import discord
from discord.ext import commands

from Cogs.Commands import Commands
from Cogs.Member import Member
from Cogs.RoleAssign import RoleAssign
from Cogs.Twitch import Twitch

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='>', intents=intents)
bot.remove_command('help')


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='Use >help'))


if __name__ == "__main__":
    if str(os.environ["EXE_MODE"]) == "0":
        DATA = json.loads(str(os.environ["TEST_DATA"]))
    else:
        DATA = json.loads(os.getenv("MAIN_DATA"))

    bot.add_cog(Member(bot, server=DATA["server_name"]))
    bot.add_cog(Commands(bot, owner=os.environ["OWNER"], server_id=DATA["server_id"]))
    bot.add_cog(Twitch(bot, header=os.environ["TWITCH"], server=DATA["server_name"], channel=DATA["twitch_channel"]))
    bot.add_cog(
        RoleAssign(bot=bot, owner=os.environ["OWNER"], server_id=DATA["server_id"],
                   channel_id=DATA["self_assign_channel"],
                   identifier_color=os.environ["IDENTIFIER_COLOR"], special_roles=os.environ["SPECIAL_ROLE"]))

    bot.run(DATA["TOKEN"])
