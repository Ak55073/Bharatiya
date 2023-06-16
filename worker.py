import os
import psycopg2 as psycopg2
from json import loads

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
    db_connection = psycopg2.connect(
        database=data["Database"],
        user=data["User"],
        password=data["Password"],
        host=data["Host"],
        port=data["Port"],
        keepalives=1,
        keepalives_idle=5,
        keepalives_interval=2,
        keepalives_count=2
    )
    db_cursor = db_connection.cursor()

    # Dynamically setting bot owner id.
    app_info = await bot.application_info()
    bot.owner_id = app_info.owner.id

    # Adding Server Management Cog
    await bot.add_cog(RoleManagerCog(bot, data, db_connection, db_cursor))

    # Cog containing miscellaneous commands
    await bot.add_cog(Commands(bot, db_connection, db_cursor))

    # Cog sends join/leave notification of server members.
    await bot.add_cog(MemberManagerCog(bot, data, db_connection, db_cursor))

    await bot.tree.sync()

    # Changing bot Activity
    await bot.change_presence(activity=discord.Game(name='use >help'))


def read_config() -> dict:
    try:
        # Reading variable through config.json, if present
        env_data = loads(open("config.json", "r").read())
    except FileNotFoundError:
        # Recommended for Security Reasons
        # Reading variable through environment variable
        # ONLY when config.json not found
        env_data = os.environ

    env_var = dict()
    env_var["DEBUG_MODE"] = bool(int(env_data["DEBUG_MODE"]))
    env_var["DM_OWNER"] = bool(int(env_data["DM_OWNER"]))
    env_var["DEBUG_TOKEN"] = env_data["DEBUG_TOKEN"]
    env_var["MAIN_TOKEN"] = env_data["MAIN_TOKEN"]

    env_var["Database"] = env_data["Database"]
    env_var["User"] = env_data["User"]
    env_var["Password"] = env_data["Password"]
    env_var["Host"] = env_data["Host"]
    env_var["Port"] = int(env_data["Port"])

    return env_var


if __name__ == "__main__":
    data = read_config()
    if data["DEBUG_MODE"]:
        bot.run(data["DEBUG_TOKEN"])
    else:
        bot.run(data["MAIN_TOKEN"])
