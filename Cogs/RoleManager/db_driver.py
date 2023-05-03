from . import data_structures as models


class RoleManagerDatabase:
    def __init__(self, conn, cur):
        self.con = conn
        self.cur = cur

    def create_auto_assign(self):
        self.cur.execute("""
            CREATE TABLE rm_servers (server_id INT PRIMARY KEY, enabled INT, channel_id INT, color_hex TEXT)""")
        self.cur.execute("CREATE TABLE rm_roles (server_id INT, role_id INT NOT NULL UNIQUE)")
        self.con.commit()

    def insert_rm_server(self, server_id: int, color: str = "#607d8b", enabled: bool = True):
        text = f"""
            INSERT INTO rm_servers (server_id, enabled, channel_id, color_hex) 
            VALUES ({server_id}, {int(enabled)}, "null", '{color}')"""
        self.cur.execute(text)
        self.con.commit()

    def update_rm_color(self, server_id: int, color: str = "#607d8b"):
        self.cur.execute(f"UPDATE rm_servers set color_hex='{color}' where server_id={server_id}")
        self.con.commit()

    def update_rm_channel(self, server_id: int, channel_id: int | None = None):
        if channel_id is None:
            channel_id = "null"
        self.cur.execute(f"UPDATE rm_servers set channel_id={channel_id} where server_id={server_id}")
        self.con.commit()

    def update_rm_enable(self, server_id: int, enable: bool):
        self.cur.execute(f"UPDATE rm_servers set enabled={int(enable)} where server_id={server_id}")
        self.con.commit()

    def update_rm_server(self, server_id: int, color: str, channel_id: int | None = None):
        text = f"""UPDATE rm_servers set channel_id={channel_id if channel_id else 'null'}, 
            color_hex='{color}' where server_id={server_id}"""
        self.cur.execute(text)
        self.con.commit()

    def fetch_rm_server(self, server_id: int) -> models.RMServersModel | None:
        self.cur.execute(f"select * from rm_servers where server_id == {server_id}")
        data = self.cur.fetchone()
        if data:
            return models.RMServersModel(server_id=data[0], enabled=data[1],
                                         channel_id=data[2], color=data[3])
        return None

    def fetch_all_rm_servers(self) -> list[models.RMServersModel]:
        self.cur.execute(f"select * from rm_servers where enabled == 1 AND channel_id IS NOT NULL")
        return [models.RMServersModel(server_id=data[0], enabled=data[1], channel_id=data[2], color=data[3])
                for data in self.cur.fetchall()]

    def insert_rm_role(self, server_id: int, role_id: int):
        self.cur.execute(f"insert into rm_roles values ({server_id}, {role_id})")
        self.con.commit()

    def delete_rm_role(self, role_id: int) -> bool:
        self.cur.execute(f"DELETE FROM rm_roles WHERE role_id={role_id}")
        # TODO: See if row count can be wrote at last
        row_count = self.cur.rowcount
        self.con.commit()
        return bool(row_count)

    def delete_all_rm_roles(self, server_id: int) -> bool:
        self.cur.execute(f"DELETE FROM rm_roles WHERE server_id={server_id}")
        affect = self.cur.rowcount
        self.con.commit()
        return bool(affect)

    def fetch_rm_roles_set(self, server_id: int) -> set[int]:
        self.cur.execute(f"select role_id from rm_roles where server_id == {server_id}")
        return {i[0] for i in self.cur.fetchall()}

    def delete_rm_record(self, server_id):
        self.cur.execute(f"DELETE FROM rm_servers WHERE server_id={server_id}")
        self.cur.execute(f"DELETE FROM rm_roles WHERE server_id={server_id}")
        self.con.commit()

    def __del__(self):
        self.con.close()
