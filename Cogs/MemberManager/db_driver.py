from .data_structures import ServerData


class MemberManagerDatabase:
    def __init__(self, conn, cur):
        self.con = conn
        self.cur = cur

    def create_meta(self):
        self.cur.execute(
            """CREATE TABLE member_manager_meta (
            server_id BIGINT PRIMARY KEY, message TEXT, enable BOOLEAN NOT NULL, 
            channel_id BIGINT UNIQUE, role_id BIGINT UNIQUE )"""
        )
        self.con.commit()

    def insert_meta(self, server_id: int, channel_id: int, role_id: int | None = None,
                    enable: bool = True, message: str = "Enjoy your stay."):

        message = message.replace("'", "\"", -1)
        text = f"INSERT INTO member_manager_meta VALUES (" \
               f"{server_id}, '{message}', {enable}, {channel_id}, {role_id})"
        self.cur.execute(text)
        self.con.commit()

    def fetch_meta(self, server_id) -> ServerData | None:
        self.cur.execute(f"select * from member_manager_meta where server_id = {server_id}")
        data = self.cur.fetchone()
        # TODO: Change
        if data:
            return ServerData(server_id=data[0], message=data[1], enable=bool(data[2]),
                              channel_id=data[3], role_id=data[4])
        return None

    def update_meta_message(self, server_id: int, message: str = "Enjoy your stay."):
        message = message.replace("\'", "\"", -1)
        text = f"UPDATE member_manager_meta set message='{message}' where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_meta_enable(self, server_id: int, enable: bool = True):
        text = f"UPDATE member_manager_meta set enable={enable} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_meta_channel(self, server_id: int, channel_id: int):
        if channel_id is None:
            return
        text = f"UPDATE member_manager_meta set channel_id={channel_id} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_meta_role(self, server_id: int, role_id: int | None = None):
        if role_id is None:
            role_id = 'null'
        text = f"UPDATE member_manager_meta set role_id={role_id} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def delete_meta(self, server_id: int):
        self.cur.execute(f"DELETE FROM member_manager_meta WHERE server_id={server_id}")
        self.con.commit()

    def __del__(self):
        self.con.close()
