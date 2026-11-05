import hashlib
import json
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
from validation import validate_schedule


def get_weekly_schedule_fingerprint(
    week_start,
    db_engine=None,
    session=None
):
    current_engine = db_engine if db_engine is not None else engine

    def calculate(current_session):
        week_end = week_start + timedelta(days=7)

        employees = current_session.scalars(
            select(EmployeeDB)
        ).all()

        shifts = current_session.scalars(
            select(ShiftDB).where(
                ShiftDB.date >= week_start,
                ShiftDB.date < week_end
            )
        ).all()

        shift_ids = [shift.shift_id for shift in shifts]

        availabilities = current_session.scalars(
            select(AvailabilityDB).where(
                AvailabilityDB.shift_id.in_(shift_ids)
            )
        ).all()

        assignments = current_session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.shift_id.in_(shift_ids)
            )
        ).all()

        weekly_schedule = current_session.get(
            WeeklyScheduleDB,
            week_start
        )

        data = {
            "week_start": week_start.isoformat(),
            "employees": sorted([
                (
                    e.employee_id,
                    e.name,
                    e.max_shifts,
                    e.preferred_shifts
                )
                for e in employees
            ]),
            "shifts": sorted([
                (
                    s.shift_id,
                    str(s.date),
                    str(s.start_time),
                    str(s.end_time),
                    s.required_employees
                )
                for s in shifts
            ]),
            "availabilities": sorted([
                (
                    a.employee_id,
                    a.shift_id,
                    str(a.status)
                )
                for a in availabilities
            ]),
            "assignments": sorted([
                (
                    a.employee_id,
                    a.shift_id
                )
                for a in assignments
            ]),
            "schedule_status": (
                weekly_schedule.status
                if weekly_schedule is not None
                else "draft"
            )
        }

        serialized = json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    if session is not None:
        return calculate(session)

    with Session(current_engine) as current_session:
        return calculate(current_session)

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
    db_engine=None,
    expected_fingerprint=None
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
            if expected_fingerprint is not None:
                current_fingerprint = (
                    get_weekly_schedule_fingerprint(
                        week_start,
                        session=session
                    )
                )

                if current_fingerprint != expected_fingerprint:
                    raise ValueError(
                        "Schedule data has changed. "
                        "Generate a new preview before approving."
                    )
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


            # Validate the exact assignments shown to the manager.
            employee_ids = {
                employee.employee_id for employee in employees
            }
            shift_id_set = {
                shift.shift_id for shift in shifts
            }

            if any(
                employee_id not in employee_ids
                or shift_id not in shift_id_set
                for employee_id, shift_id in expected_pairs
            ):
                raise ValueError(
                    "Schedule has changed. "
                    "Generate a new preview before approving."
                )

            from assignment import Assignment

            proposed_assignments = existing_assignments + [
                Assignment(employee_id, shift_id)
                for employee_id, shift_id in sorted(expected_pairs)
            ]

            validation_errors = validate_schedule(
                employees,
                shifts,
                availabilities,
                proposed_assignments
            )

            if validation_errors:
                raise ValueError(
                    "Schedule has changed. "
                    "Generate a new preview before approving."
                )

            # Compare quality, not the identity of assignments.
            def schedule_quality(schedule):
                counts = {
                    employee.employee_id: 0
                    for employee in employees
                }

                for assignment in schedule:
                    counts[assignment.employee_id] += 1

                preference_deviation = sum(
                    abs(
                        counts[employee.employee_id]
                        - employee.preferred_shifts
                    )
                    for employee in employees
                )

                loads = list(counts.values())
                fairness_gap = (
                    max(loads) - min(loads)
                    if loads else 0
                )

                preference_weight = len(shifts) + 1

                return (
                    len(schedule),
                    -(
                        preference_weight * preference_deviation
                        + fairness_gap
                    )
                )

            if (
                schedule_quality(proposed_assignments)
                < schedule_quality(fresh_preview)
            ):
                raise ValueError(
                    "Schedule has changed. "
                    "Generate a new preview before approving."
                )

            for assignment in proposed_assignments:
                if (
                        assignment.employee_id,
                        assignment.shift_id
                ) in saved_pairs:
                    continue
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

    return len(expected_pairs)

