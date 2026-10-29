
from pathlib import Path

from sqlalchemy import create_engine, text, inspect, event
from database.models import (
    Base,
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    AssignmentDB,
    StaffingRequestDB
)


# Project root folder
BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite database file
DATABASE_PATH = BASE_DIR / "smartshift.db"

# Create the database engine
engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    old_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    dbapi_connection.autocommit = old_autocommit



def test_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        return result.scalar_one()


if __name__ == "__main__":
    print("Database connection:", test_connection())

    Base.metadata.create_all(engine)
    print("Database tables:", inspect(engine).get_table_names())

    print("Employees table created successfully!")
    print("Database file:", DATABASE_PATH)
    with engine.connect() as connection:
        foreign_keys_enabled = connection.execute(
            text("PRAGMA foreign_keys")
        ).scalar_one()

        print("Foreign keys enabled:", foreign_keys_enabled)
