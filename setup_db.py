import psycopg2 as psycopg2

from Cogs.RoleManager.db_driver import RoleManagerDatabase
from Cogs.MemberManager.db_driver import MemberManagerDatabase

from worker import read_config


def setup_role_manager():
    db_connection = psycopg2.connect(
        database=data["Database"],
        user=data["User"],
        password=data["Password"],
        host=data["Host"],
        port=data["Port"],
    )
    db_cursor = db_connection.cursor()

    try:
        role_manager = RoleManagerDatabase(db_connection, db_cursor)
        role_manager.create_auto_assign()
    except psycopg2.OperationalError:
        pass

    try:
        member_manager = MemberManagerDatabase(db_connection, db_cursor)
        member_manager.create_meta()
    except psycopg2.OperationalError:
        pass

    db_connection.close()


if __name__ == "__main__":
    data = read_config()
    setup_role_manager()
