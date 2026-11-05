
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from database.db import engine
from database.models import WeeklyDeadlineDB


ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")


def save_weekly_deadline(
    week_start,
    deadline_date,
    deadline_time,
    db_engine=None
):
    if not isinstance(week_start, date):
        raise ValueError("Invalid week start")

    if week_start.weekday() != 6:
        raise ValueError("Week must start on Sunday")

    deadline_at = datetime.combine(
        deadline_date,
        deadline_time
    )

    # The deadline must be before the week begins.
    if deadline_at.date() >= week_start:
        raise ValueError(
            "Deadline must be before the selected week"
        )

    current_engine = (
        db_engine if db_engine is not None else engine
    )

    with Session(current_engine) as session:
        with session.begin():
            existing_deadline = session.get(
                WeeklyDeadlineDB,
                week_start
            )

            if existing_deadline is None:
                session.add(
                    WeeklyDeadlineDB(
                        week_start=week_start,
                        deadline_at=deadline_at
                    )
                )
            else:
                existing_deadline.deadline_at = deadline_at

    return True


def get_weekly_deadline(week_start, db_engine=None):
    current_engine = (
        db_engine if db_engine is not None else engine
    )

    with Session(current_engine) as session:
        deadline = session.get(
            WeeklyDeadlineDB,
            week_start
        )

        if deadline is None:
            return None

        return deadline.deadline_at
