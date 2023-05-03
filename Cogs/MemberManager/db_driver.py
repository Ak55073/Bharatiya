from .data_structures import ServerData


class MemberManagerDatabase:
    def __init__(self, conn, cur):
        self.con = conn
        self.cur = cur

    def create_mm_data(self):
        self.cur.execute("""CREATE TABLE member_manage 
            (server_id INT PRIMARY KEY, message TEXT, enable INT, channel_id INT, role_id INT)""")
        self.con.commit()

    def insert_server(self, server_id: int, channel_id: int, role_id: int | None = None,
                      enable: bool = True, message: str = "Enjoy your stay."):
        message = message.replace("'", "\"", -1)
        text = f"""INSERT INTO member_manage (server_id, message, enable, channel_id, role_id) 
            VALUES ({server_id}, '{message}', {int(enable)}, {channel_id}, {role_id})"""
        self.cur.execute(text)
        self.con.commit()

    def fetch_server(self, server_id) -> ServerData | None:
        self.cur.execute(f"select * from member_manage where server_id == {server_id}")
        data = self.cur.fetchone()
        if data:
            return ServerData(server_id=data[0], message=data[1], enable=bool(data[2]),
                              channel_id=data[3], role_id=data[4])
        return None

    def update_message(self, server_id: int, message: str = "Enjoy your stay."):
        message = message.replace("\'", "\"", -1)
        text = f"UPDATE member_manage set message='{message}' where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_enable(self, server_id: int, enable: bool = True):
        text = f"UPDATE member_manage set enable={int(enable)} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_channel(self, server_id: int, channel_id: int):
        if channel_id is None:
            return
        text = f"UPDATE member_manage set channel_id={channel_id} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def update_role(self, server_id: int, role_id: int | None = None):
        text = f"UPDATE member_manage set role_id={role_id if role_id else 'null'} where server_id={server_id}"
        self.cur.execute(text)
        self.con.commit()

    def delete_server(self, server_id: int):
        self.cur.execute(f"DELETE FROM member_manage WHERE server_id={server_id}")
        self.con.commit()

    def __del__(self):
        self.con.close()