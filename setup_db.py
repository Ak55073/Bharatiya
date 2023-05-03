import sqlite3
from Cogs.RoleManager.db_driver import RoleManagerDatabase
from Cogs.MemberManager.db_driver import MemberManagerDatabase


def setup_role_manager():
    db_connection = sqlite3.connect("database.db")
    db_cursor = db_connection.cursor()

    try:
        role_manager = RoleManagerDatabase(db_connection, db_cursor)
        role_manager.create_auto_assign()
    except sqlite3.OperationalError:
        pass

    try:
        member_manager = MemberManagerDatabase(db_connection, db_cursor)
        member_manager.create_mm_data()
    except sqlite3.OperationalError:
        pass

    db_connection.close()


if __name__ == "__main__":
    setup_role_manager()
