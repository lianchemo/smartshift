
from datetime import date, time, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.db import engine
from database.models import ShiftDB


SHIFT_TIMES = [
    (time(8, 0), time(16, 0)),
    (time(16, 0), time(23, 0))
]


def create_weekly_shifts(
    week_start,
    required_employees=2,
    db_engine=None,
    staffing_requirements=None
):
    if not isinstance(week_start, date):
        raise ValueError("week_start must be a date")

    if week_start.weekday() != 6:
        raise ValueError("week_start must be a Sunday")

    if staffing_requirements is None:
        staffing_requirements = [required_employees] * 14

    if len(staffing_requirements) != 14:
        raise ValueError(
            "Exactly 14 staffing requirements are needed"
        )

    if any(
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 1
        for count in staffing_requirements
    ):
        raise ValueError(
            "Each shift must require at least one employee"
        )

    current_engine = db_engine if db_engine is not None else engine

    created_count = 0

    with Session(current_engine) as session:
        with session.begin():

            week_end = week_start + timedelta(days=7)

            existing_shifts = session.scalars(
                select(ShiftDB).where(
                    ShiftDB.date >= week_start,
                    ShiftDB.date < week_end
                )
            ).all()

            existing_slots = {
                (
                    shift.date,
                    shift.start_time,
                    shift.end_time
                )
                for shift in existing_shifts
            }

            max_id = session.scalar(
                select(func.max(ShiftDB.shift_id))
            )

            next_shift_id = (max_id or 0) + 1

            for day_offset in range(7):
                shift_date = (
                    week_start + timedelta(days=day_offset)
                )

                for shift_index, (start_time, end_time) in enumerate(
                    SHIFT_TIMES
                ):
                    requirement_index = (
                        day_offset * 2 + shift_index
                    )

                    employees_needed = staffing_requirements[
                        requirement_index
                    ]

                    slot = (
                        shift_date,
                        start_time,
                        end_time
                    )

                    if slot in existing_slots:
                        continue

                    session.add(
                        ShiftDB(
                            shift_id=next_shift_id,
                            date=shift_date,
                            start_time=start_time,
                            end_time=end_time,
                            required_employees=employees_needed
                        )
                    )

                    existing_slots.add(slot)
                    next_shift_id += 1
                    created_count += 1

    return created_count
