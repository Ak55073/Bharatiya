from . import data_structures as models


class RoleManagerDatabase:
    def __init__(self, conn, cur):
        self.con = conn
        self.cur = cur

    def create_auto_assign(self):
        self.cur.execute(
            """CREATE TABLE role_manager_meta (server_id BIGINT PRIMARY KEY,
            enabled BOOLEAN NOT NULL, channel_id BIGINT, color_hex TEXT NOT NULL)"""
        )
        self.cur.execute(
            """CREATE TABLE role_manager_roles (server_id BIGINT, role_id BIGINT NOT NULL UNIQUE,
            FOREIGN KEY (server_id) REFERENCES role_manager_meta(server_id) ON DELETE CASCADE);"""
        )
        self.con.commit()

    def insert_meta(self, server_id: int, color: str = "#607d8b", enabled: bool = True):
        text = f"""INSERT INTO role_manager_meta (server_id, enabled, channel_id, color_hex) 
            VALUES ({server_id}, {enabled}, {'null'}, '{color}')"""
        self.cur.execute(text)
        self.con.commit()

    def update_meta(self, server_id: int, color: str, channel_id: int | None = None):
        if channel_id is None:
            channel_id = "null"
        text = f"UPDATE role_manager_meta set channel_id={channel_id}, color_hex='{color}' where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_meta_color(self, server_id: int, color: str = "#607d8b"):
        self.cur.execute(f"UPDATE role_manager_meta set color_hex='{color}' where server_id={server_id}")
        self.con.commit()

    def update_meta_channel(self, server_id: int, channel_id: int | None = None):
        if channel_id is None:
            channel_id = "null"
        self.cur.execute(f"UPDATE role_manager_meta set channel_id={channel_id} where server_id={server_id}")
        self.con.commit()

    def update_meta_enable(self, server_id: int, enable: bool):
        self.cur.execute(f"UPDATE role_manager_meta set enabled={enable} where server_id={server_id}")
        self.con.commit()

    def fetch_one_meta(self, server_id: int) -> models.RMServersModel | None:
        self.cur.execute(f"select * from role_manager_meta where server_id = {server_id}")
        # TODO: Change
        data = self.cur.fetchone()
        if data:
            return models.RMServersModel(server_id=data[0], enabled=data[1], channel_id=data[2], color=data[3])
        return None

    def fetch_all_meta(self) -> list[models.RMServersModel]:
        self.cur.execute(f"select * from role_manager_meta where enabled is True AND channel_id IS NOT NULL")
        return [models.RMServersModel(server_id=data[0], enabled=data[1], channel_id=data[2], color=data[3])
                for data in self.cur.fetchall()]

    def insert_role(self, server_id: int, role_id: int):
        self.cur.execute(f"insert into role_manager_roles values ({server_id}, {role_id})")
        self.con.commit()

    def delete_role(self, role_id: int) -> bool:
        self.cur.execute(f"DELETE FROM role_manager_roles WHERE role_id={role_id}")
        row_count = self.cur.rowcount
        self.con.commit()
        return bool(row_count)

    def delete_all_roles(self, server_id: int) -> bool:
        self.cur.execute(f"DELETE FROM role_manager_roles WHERE server_id={server_id}")
        affect = self.cur.rowcount
        self.con.commit()
        return bool(affect)

    def fetch_roles_set(self, server_id: int) -> set[int]:
        self.cur.execute(f"select role_id from role_manager_roles where server_id = {server_id}")
        return {i[0] for i in self.cur.fetchall()}

    def delete_record(self, server_id):
        self.cur.execute(f"DELETE FROM role_manager_meta WHERE server_id={server_id}")
        self.cur.execute(f"DELETE FROM role_manager_roles WHERE server_id={server_id}")
        self.con.commit()

    def __del__(self):
        self.con.close()
