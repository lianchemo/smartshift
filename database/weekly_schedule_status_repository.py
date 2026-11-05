
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from database.db import engine
from database.models import WeeklyScheduleDB


ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")


def get_weekly_schedule_status(
    week_start,
    db_engine=None
):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        schedule = session.get(
            WeeklyScheduleDB,
            week_start
        )

        if schedule is None:
            return "draft"

        return schedule.status


def mark_weekly_schedule_approved(
    week_start,
    db_engine=None
):
    if not isinstance(week_start, date):
        raise ValueError("Invalid week start")

    if week_start.weekday() != 6:
        raise ValueError("Week must start on Sunday")

    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():
            schedule = session.get(
                WeeklyScheduleDB,
                week_start
            )

            if schedule is None:
                session.add(
                    WeeklyScheduleDB(
                        week_start=week_start,
                        status="approved"
                    )
                )

            elif schedule.status == "published":
                raise ValueError(
                    "Published schedules cannot be approved again"
                )

            else:
                schedule.status = "approved"

    return True


def publish_weekly_schedule(
    week_start,
    db_engine=None
):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():
            schedule = session.get(
                WeeklyScheduleDB,
                week_start
            )

            if schedule is None:
                raise ValueError(
                    "Schedule must be approved before publishing"
                )

            if schedule.status != "approved":
                raise ValueError(
                    "Only approved schedules can be published"
                )

            schedule.status = "published"

            schedule.published_at = datetime.now(
                ISRAEL_TIMEZONE
            ).replace(tzinfo=None)

    return True
