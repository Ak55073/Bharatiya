import os
from json import loads

import discord
from discord.ext import commands

from Cogs.Commands import Commands
from Cogs.MaintainDB import MaintainDB
from Cogs.RoleAssign import RoleAssign
from Cogs.ServerListener import ServerListener
from Cogs.Twitch import Twitch

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='>', intents=intents)
bot.remove_command('help')

if __name__ == "__main__":
    bot.add_cog(MaintainDB(bot))
    bot.add_cog(Commands(bot))
    bot.add_cog(RoleAssign(bot))
    bot.add_cog(ServerListener(bot))
    bot.add_cog(Twitch(bot))

    try:
        # For simplicity sake reading variable through config.json
        data = loads(open("config.json", "r").read())
        if not data["EXE_MODE"]:
            bot.run(data["TEST_TOKEN"])
        else:
            bot.run(data["MAIN_TOKEN"])
    except FileNotFoundError:
        # ONLY when config.json not found
        # For security sake reading variable through environment variable
        if str(os.environ["EXE_MODE"]) == "0":
            bot.run(str(os.environ["TEST_TOKEN"]))
        else:
            bot.run(str(os.environ["MAIN_TOKEN"]))
