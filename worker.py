import os
from json import loads
import sqlite3

import discord
from discord.ext import commands

from Cogs.CommandsManager.Commands import Commands
from Cogs.RoleManager.RoleManagerCog import RoleManagerCog
from Cogs.MemberManager.MemberCog import MemberManagerCog

bot = commands.Bot(command_prefix='>', intents=discord.Intents.all())
bot.remove_command('help')


@bot.event
async def on_ready():
    # Changing bot Activity
    await bot.change_presence(activity=discord.Game(name='Starting...'))

    # Initializing Database Driver
    db_connection = sqlite3.connect("database.db")
    db_cursor = db_connection.cursor()

    # Dynamically setting bot owner id.
    app_info = await bot.application_info()
    bot.owner_id = app_info.owner.id

    # Adding Server Management Cog
    # await bot.add_cog(ServerCog(bot, env_var, db_driver))
    await bot.add_cog(RoleManagerCog(bot, env_var, db_connection, db_cursor))

    # Cog containing miscellaneous commands
    await bot.add_cog(Commands(bot, db_connection, db_cursor))

    # Cog sends join/leave notification of server members.
    await bot.add_cog(MemberManagerCog(bot, env_var, db_connection, db_cursor))

    await bot.tree.sync()

    # Changing bot Activity
    await bot.change_presence(activity=discord.Game(name='use >help'))


if __name__ == "__main__":
    try:
        # Reading variable through config.json
        env_var = loads(open("config.json", "r").read())
    except FileNotFoundError:
        # Reading variable through environment variable
        # ONLY when config.json not found
        env_var = dict()
        env_var["DEBUG_MODE"] = int(os.environ["DEBUG_MODE"])
        env_var["DM_OWNER"] = int(os.environ["DM_OWNER"])
        env_var["DEBUG_TOKEN"] = os.environ["DEBUG_TOKEN"]
        env_var["MAIN_TOKEN"] = os.environ["MAIN_TOKEN"]

    if env_var["DEBUG_MODE"]:
        bot.run(env_var["DEBUG_TOKEN"])
    else:
        bot.run(env_var["MAIN_TOKEN"])
