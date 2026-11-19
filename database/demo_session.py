
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, event


BASE_DIR = Path(__file__).resolve().parent.parent

DEMO_TEMPLATE_PATH = (
    BASE_DIR / "smartshift_demo_template.db"
)


def create_demo_engine():
    """
    Create an isolated temporary database for a demo visitor.

    Returns:
        engine: SQLAlchemy engine for the visitor's database.
        database_path: Path to the temporary database file.
    """

    if not DEMO_TEMPLATE_PATH.is_file():
        raise FileNotFoundError(
            "Demo database template was not found."
        )

    temporary_file = tempfile.NamedTemporaryFile(
        prefix="smartshift_visitor_",
        suffix=".db",
        delete=False
    )

    database_path = Path(temporary_file.name)
    temporary_file.close()

    try:
        shutil.copy2(
            DEMO_TEMPLATE_PATH,
            database_path
        )

        demo_engine = create_engine(
            f"sqlite:///{database_path.as_posix()}"
        )

        @event.listens_for(demo_engine, "connect")
        def enable_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return demo_engine, database_path

    except Exception:
        database_path.unlink(missing_ok=True)
        raise
