
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import (
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    AssignmentDB,
    WeeklyScheduleDB
)

from database.converters import (
    employee_from_db,
    shift_from_db,
    availability_from_db,
    assignment_from_db
)

from optimizer import optimize_schedule


def generate_weekly_schedule_preview(
    week_start=None,
    db_engine=None
):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:

        # Load shifts for the selected week only
        shift_query = select(ShiftDB)

        if week_start is not None:
            week_end = week_start + timedelta(days=7)

            shift_query = shift_query.where(
                ShiftDB.date >= week_start,
                ShiftDB.date < week_end
            )

        shift_rows = session.scalars(shift_query).all()

        shifts = [
            shift_from_db(row)
            for row in shift_rows
        ]

        # No shifts in the selected week
        if not shifts:
            return []

        shift_ids = [
            shift.shift_id
            for shift in shifts
        ]

        employees = [
            employee_from_db(row)
            for row in session.scalars(
                select(EmployeeDB)
            )
        ]

        # Only availability for selected shifts
        availability_rows = session.scalars(
            select(AvailabilityDB).where(
                AvailabilityDB.shift_id.in_(shift_ids)
            )
        ).all()

        availabilities = [
            availability_from_db(row)
            for row in availability_rows
        ]

        # Preserve assignments in selected week
        assignment_rows = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.shift_id.in_(shift_ids)
            )
        ).all()

        existing_assignments = [
            assignment_from_db(row)
            for row in assignment_rows
        ]

    preview = optimize_schedule(
        employees,
        shifts,
        availabilities,
        existing_assignments=existing_assignments
    )

    return preview

def approve_weekly_schedule(
    week_start,
    expected_new_assignments,
    db_engine=None
):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB,
        AssignmentDB
    )

    current_engine = db_engine if db_engine is not None else engine

    if not isinstance(week_start, date):
        raise ValueError("Invalid week start")

    if week_start.weekday() != 6:
        raise ValueError("Week must start on Sunday")

    expected_pairs = {
        (assignment.employee_id, assignment.shift_id)
        for assignment in expected_new_assignments
    }

    if len(expected_pairs) != len(expected_new_assignments):
        raise ValueError("Duplicate proposed assignments")

    with Session(current_engine) as session:
        with session.begin():
            # Do not modify an already published schedule.
            weekly_schedule = session.get(
                WeeklyScheduleDB,
                week_start
            )

            if (
                weekly_schedule is not None
                and weekly_schedule.status == "published"
            ):
                raise ValueError(
                    "Published schedules cannot be modified"
                )
            week_end = week_start + timedelta(days=7)

            shift_rows = session.scalars(
                select(ShiftDB).where(
                    ShiftDB.date >= week_start,
                    ShiftDB.date < week_end
                )
            ).all()

            shifts = [
                shift_from_db(row)
                for row in shift_rows
            ]

            if not shifts:
                raise ValueError(
                    "No shifts exist for the selected week"
                )

            shift_ids = [
                shift.shift_id
                for shift in shifts
            ]

            employees = [
                employee_from_db(row)
                for row in session.scalars(
                    select(EmployeeDB)
                ).all()
            ]

            availabilities = [
                availability_from_db(row)
                for row in session.scalars(
                    select(AvailabilityDB).where(
                        AvailabilityDB.shift_id.in_(shift_ids)
                    )
                ).all()
            ]

            existing_assignments = [
                assignment_from_db(row)
                for row in session.scalars(
                    select(AssignmentDB).where(
                        AssignmentDB.shift_id.in_(shift_ids)
                    )
                ).all()
            ]

            saved_pairs = {
                (assignment.employee_id, assignment.shift_id)
                for assignment in existing_assignments
            }

            fresh_preview = optimize_schedule(
                employees,
                shifts,
                availabilities,
                existing_assignments=existing_assignments
            )

            fresh_new_assignments = [
                assignment
                for assignment in fresh_preview
                if (
                    assignment.employee_id,
                    assignment.shift_id
                ) not in saved_pairs
            ]

            fresh_pairs = {
                (assignment.employee_id, assignment.shift_id)
                for assignment in fresh_new_assignments
            }

            if fresh_pairs != expected_pairs:
                raise ValueError(
                    "Schedule has changed. "
                    "Generate a new preview before approving."
                )

            for assignment in fresh_new_assignments:
                session.add(
                    AssignmentDB(
                        employee_id=assignment.employee_id,
                        shift_id=assignment.shift_id
                    )
                )
            # Mark the week as approved in the same transaction.
            if weekly_schedule is None:
                session.add(
                    WeeklyScheduleDB(
                        week_start=week_start,
                        status="approved"
                    )
                )
            else:
                weekly_schedule.status = "approved"

    return len(fresh_new_assignments)

