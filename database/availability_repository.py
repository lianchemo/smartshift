
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import AvailabilityDB


def add_availabilities(availabilities):
    added_count = 0

    with Session(engine) as session:
        for availability in availabilities:
            statement = select(AvailabilityDB).where(
                AvailabilityDB.employee_id == availability.employee_id,
                AvailabilityDB.shift_id == availability.shift_id
            )

            existing = session.scalar(statement)

            if existing is not None:
                continue

            db_availability = AvailabilityDB(
                employee_id=availability.employee_id,
                shift_id=availability.shift_id,
                status=availability.status.value
            )

            session.add(db_availability)
            added_count += 1

        session.commit()

    print(f"Added {added_count} availability records.")


def get_all_availabilities():
    with Session(engine) as session:
        statement = select(AvailabilityDB).order_by(
            AvailabilityDB.employee_id,
            AvailabilityDB.shift_id
        )

        return session.scalars(statement).all()



def update_availability(
    employee_id,
    shift_id,
    new_status,
    db_engine=None
):
    valid_statuses = {
        "available",
        "flexible",
        "unavailable"
    }

    if new_status not in valid_statuses:
        raise ValueError("Invalid availability status")

    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        statement = select(AvailabilityDB).where(
            AvailabilityDB.employee_id == employee_id,
            AvailabilityDB.shift_id == shift_id
        )

        availability = session.scalar(statement)

        if availability is None:
            raise ValueError("Availability record not found")

        availability.status = new_status
        session.commit()

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from sample_data import (
        create_sample_employees,
        create_sample_shifts,
        create_sample_availabilities
    )

    employees = create_sample_employees()
    shifts = create_sample_shifts()

    availabilities = create_sample_availabilities(
        employees,
        shifts
    )

    add_availabilities(availabilities)

    saved_availabilities = get_all_availabilities()

    print(
        "Total availabilities in database:",
        len(saved_availabilities)
    )

    print("\nFirst 5 availability records:")

    for availability in saved_availabilities[:5]:
        print(
            availability.employee_id,
            availability.shift_id,
            availability.status
        )

def save_employee_availability(
    employee_id,
    shift_id,
    new_status,
    db_engine=None
):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from database.db import engine
    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB,
        AssignmentDB
    )

    allowed_statuses = {
        "available",
        "flexible",
        "unavailable"
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid availability status")

    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():

            employee = session.get(EmployeeDB, employee_id)
            shift = session.get(ShiftDB, shift_id)

            if employee is None:
                raise ValueError("Employee not found")

            if shift is None:
                raise ValueError("Shift not found")

            # Do not change availability for assigned shifts
            existing_assignment = session.scalar(
                select(AssignmentDB).where(
                    AssignmentDB.employee_id == employee_id,
                    AssignmentDB.shift_id == shift_id
                )
            )

            if existing_assignment is not None:
                raise ValueError(
                    "Cannot change availability for "
                    "an assigned shift"
                )

            availability = session.scalar(
                select(AvailabilityDB).where(
                    AvailabilityDB.employee_id == employee_id,
                    AvailabilityDB.shift_id == shift_id
                )
            )

            if availability is None:
                availability = AvailabilityDB(
                    employee_id=employee_id,
                    shift_id=shift_id,
                    status=new_status
                )
                session.add(availability)

            else:
                availability.status = new_status

    return True

def save_weekly_availability(
    employee_id,
    shift_statuses,
    db_engine=None
):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from database.db import engine
    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB,
        AssignmentDB
    )

    allowed_statuses = {
        "available",
        "flexible",
        "unavailable"
    }

    current_engine = db_engine if db_engine is not None else engine

    if not isinstance(shift_statuses, dict):
        raise ValueError("shift_statuses must be a dictionary")

    if any(
        status not in allowed_statuses
        for status in shift_statuses.values()
    ):
        raise ValueError("Invalid availability status")


    # ----------------------------------------------
    # Check weekly submission deadline
    # ----------------------------------------------

    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from database.models import WeeklyDeadlineDB

    israel_timezone = ZoneInfo("Asia/Jerusalem")
    now_in_israel = datetime.now(israel_timezone)

    with Session(current_engine) as deadline_session:
        shift_dates = []

        for shift_id in shift_statuses:
            shift = deadline_session.get(ShiftDB, shift_id)

            if shift is None:
                raise ValueError(
                    f"Shift {shift_id} not found"
                )

            shift_dates.append(shift.date)

        week_starts = {
            shift_date - timedelta(
                days=(shift_date.weekday() + 1) % 7
            )
            for shift_date in shift_dates
        }

        if len(week_starts) > 1:
            raise ValueError(
                "All submitted shifts must belong "
                "to the same week"
            )

        if week_starts:
            week_start = next(iter(week_starts))

            deadline = deadline_session.get(
                WeeklyDeadlineDB,
                week_start
            )

            if deadline is not None:
                deadline_in_israel = (
                    deadline.deadline_at.replace(
                        tzinfo=israel_timezone
                    )
                )

                if now_in_israel > deadline_in_israel:
                    raise ValueError(
                        "The availability submission "
                        "deadline has passed"
                    )


    with Session(current_engine) as session:
        with session.begin():

            employee = session.get(EmployeeDB, employee_id)

            if employee is None:
                raise ValueError("Employee not found")

            for shift_id, status in shift_statuses.items():

                shift = session.get(ShiftDB, shift_id)

                if shift is None:
                    raise ValueError(
                        f"Shift {shift_id} not found"
                    )

                existing_assignment = session.scalar(
                    select(AssignmentDB).where(
                        AssignmentDB.employee_id == employee_id,
                        AssignmentDB.shift_id == shift_id
                    )
                )

                if existing_assignment is not None:
                    raise ValueError(
                        f"Shift {shift_id} is already assigned"
                    )

                availability = session.scalar(
                    select(AvailabilityDB).where(
                        AvailabilityDB.employee_id == employee_id,
                        AvailabilityDB.shift_id == shift_id
                    )
                )

                if availability is None:
                    session.add(
                        AvailabilityDB(
                            employee_id=employee_id,
                            shift_id=shift_id,
                            status=status
                        )
                    )
                else:
                    availability.status = status

    return len(shift_statuses)

