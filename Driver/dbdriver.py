import discord
import pymongo


class DBManage:
    def __init__(self, url):
        self.client = pymongo.MongoClient(url)
        self.db = self.client.AppData

    async def startup(self, bot):
        # Create New Database and Collection
        if "AppData" not in self.client.list_database_names() \
                or "servers" not in self.db.list_collection_names() \
                or self.db.servers.count() == 0:
            for guild in bot.guilds:
                self.server_join(guild)

        # Update Existing Collection
        else:
            server_list = self.db.servers.distinct("id")
            for guild in bot.guilds:
                # Ignoring Server; If it's already in DB
                if guild.id in server_list:
                    server_list.remove(guild.id)
                # Adding new server to DB
                else:
                    self.server_join(guild)

            # Removing server from DB; If bot have been removed from the said server
            if server_list:
                for i in server_list:
                    self.db.servers.remove({"id": i})

        # Validating members collection
        if "AppData" in self.client.list_database_names() \
                and "members" in self.db.list_collection_names() \
                and self.db.members.count() == 0:
            for member_data in self.db.members.find():
                if not member_data["in_server"]:
                    continue
                for server_id in member_data["in_server"]:
                    try:
                        server_ob = bot.get_guild(server_id)
                        try:
                            server_ob.get_member(member_data["id"])
                        except discord.errors.NotFound:
                            # If member is not found in the server
                            # Server id is removed from member data
                            member_data["in_server"].remove(server_ob.id)
                            if member_data["blocked_from"] and server_ob.id in member_data["blocked_from"]:
                                member_data["blocked_from"].remove(server_id.id)
                            self.db.members.update({'id': member_data["id"]}, {'$set': {
                                "in_server": member_data["in_server"],
                                "blocked_from": member_data["blocked_from"]
                            }}, multi=False)
                    except discord.errors.Forbidden:
                        # If bot is not in the given server
                        # Server id is removed from member data
                        member_data["in_server"].remove(server_id)
                        if member_data["blocked_from"] and server_id in member_data["blocked_From"]:
                            member_data["blocked_Fro"].remove(server_id)
                        self.db.members.update({'id': member_data["id"]}, {'$set': {
                            "in_server": member_data["in_server"],
                            "blocked_from": member_data["blocked_from"]
                        }}, multi=False)

    def server_join(self, guild):
        server = {
            "id": guild.id,
            "name": guild.name,
            "new_member_notification": {
                "enable": False,
                "message": None,
                "role": None,
                "channel": None
            },
            "twitch_notification": {
                "enable": False,
                "twitch_channel": None,
                "other_streamer": None
            },
            "self_assign": {
                "enable": False,
                "channel": None,
                "color": None,
                "show_members": False,
                "special_role": None
            },
            "auto_role": False,
        }
        self.db.servers.insert_one(server)

    def server_update_name(self, guild):
        self.db.servers.update({'id': guild.id}, {'$set': {'name': guild.name}}, multi=False)

    def server_update_member(self, guild_id, append_message, role, channel, enable=True):
        self.db.servers.update({'id': guild_id}, {'$set': {
            "new_member_notification": {
                "enable": enable,
                "message": append_message,
                "role": role,
                "channel": channel
            }
        }}, multi=False)

    def server_update_twitch(self, guild_id, channel, enable=True):
        self.db.servers.update({'id': guild_id}, {'$set': {
            "twitch_notification.enable": enable,
            "twitch_notification.twitch_channel": channel
        }}, multi=False)

    def server_update_twitch_streamer(self, guild_id, streamer):
        self.db.servers.update({'id': guild_id}, {'$set': {
            "twitch_notification.other_streamer": streamer
        }}, multi=False)

    def server_update_twitch_streamer_status(self, guild_id, pos, live):
        self.db.servers.update(
            {'id': guild_id, "twitch_notification.other_streamer": {"$elemMatch": {"username": pos}}},
            {'$set': {"twitch_notification.other_streamer.$.live_status": live}}, multi=False)

    def server_update_self_assign(self, guild_id, channel, color, role, show_member, enable=True):
        self.db.servers.update({'id': guild_id}, {'$set': {
            "self_assign": {
                "enable": enable,
                "channel": channel,
                "color": color,
                "show_members": show_member,
                "special_role": role
            }
        }}, multi=False)

    def server_update_auto_role(self, guild_id, enable):
        self.db.servers.update({'id': guild_id}, {'$set': {
            "auto_role": enable
        }}, multi=False)

    def server_query_data(self, guild_id, mode=None):
        if mode == "new_member":
            data = self.db.servers.find_one({'id': guild_id},
                                            {"new_member_notification": 1, "_id": 0})
            return data["new_member_notification"] if data else None

        elif mode == "twitch":
            data = self.db.servers.find_one({'id': guild_id},
                                            {"twitch_notification": 1, "_id": 0})
            return data["twitch_notification"] if data else None

        elif mode == "twitch_followed":
            data = self.db.servers.find({'twitch_notification.other_streamer': {"$gt": []}},
                                        {"id": 1, 'twitch_notification': 1, "_id": 0})
            return data

        elif mode == "self_assign":
            data = self.db.servers.find_one({'id': guild_id},
                                            {'self_assign': 1, "_id": 0})
            return data['self_assign'] if data else None

        elif mode == "self_assign_all":
            return self.db.servers.find({"self_assign.enable": True},
                                        {'id': 1, 'self_assign': 1, "_id": 0})
        elif mode == "auto_assign":
            return self.db.servers.find_one({'id': guild_id},
                                            {'auto_role': 1, "_id": 0})
        elif mode == "help":
            return self.db.servers.find_one({'id': guild_id}, {
                'twitch_notification.enable': 1,
                'self_assign.enable': 1,
                'auto_role': 1,
                'new_member_notification.enable': 1,
            })
        else:
            return self.db.servers.find_one({'id': guild_id})

    def server_delete_data(self, guild_id):
        self.db.servers.delete_one({'id': guild_id})

    def member_add_data(self, member_id, twitch_username, guild_id):
        member = {
            "id": member_id,
            "twitch_username": twitch_username,
            "in_server": [guild_id, ],
            "blocked_from": None,
            "live_status": False,
        }
        self.db.members.insert_one(member)

    def member_update_server(self, member_id, server_list, blocked_list):
        if server_list and blocked_list:
            self.db.members.update({'id': member_id}, {'$set': {
                "in_server": server_list,
                "blocked_from": blocked_list
            }}, multi=False)
        elif blocked_list:
            self.db.members.update({'id': member_id}, {'$set': {
                "blocked_from": blocked_list,
            }}, multi=False)
        if server_list:
            self.db.members.update({'id': member_id}, {'$set': {
                "in_server": server_list,
            }}, multi=False)

    def member_update_status(self, member_id, status):
        self.db.members.update({'id': member_id}, {'$set': {
            "live_status": status,
        }}, multi=False)

    def member_query_data(self, member_id, mode):
        if mode == "one":
            return self.db.members.find_one({'id': member_id})
        elif mode == "server_list":
            return self.db.members.find_one({'id': member_id}, {'in_server': 1, 'blocked_from': 1, "_id": 0})
        else:
            return self.db.members.find()

    def member_data_delete(self, member):
        self.db.servers.delete_one({'id': member})
