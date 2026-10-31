
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.db import engine
from database.models import (
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    AssignmentDB,
    StaffingRequestDB
)


def approve_staffing_request(request_id, db_engine=None):
    current_engine = db_engine if db_engine is not None else engine

    # Both changes are part of one transaction
    with Session(current_engine) as session:
        with session.begin():
            request = session.get(
                StaffingRequestDB,
                request_id
            )

            if request is None:
                raise ValueError("Staffing request not found")

            if request.status != "pending":
                raise ValueError("Only pending requests can be approved")

            statement = select(AvailabilityDB).where(
                AvailabilityDB.employee_id == request.employee_id,
                AvailabilityDB.shift_id == request.shift_id
            )

            availability = session.scalar(statement)

            if availability is None:
                raise ValueError(
                    "Availability record not found"
                )

            if availability.status != "flexible":
                raise ValueError(
                    "Employee is not flexible for this shift"
                )

            # Update both objects
            request.status = "accepted"
            availability.status = "available"

def accept_and_assign_request(request_id, db_engine=None):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():

            # 1. Find the pending request
            request = session.get(
                StaffingRequestDB,
                request_id
            )

            if request is None:
                raise ValueError("Request not found")

            if request.status != "pending":
                raise ValueError(
                    "Only pending requests can be accepted"
                )

            # 2. Find employee and shift
            employee = session.get(
                EmployeeDB,
                request.employee_id
            )

            shift = session.get(
                ShiftDB,
                request.shift_id
            )

            if employee is None or shift is None:
                raise ValueError(
                    "Employee or shift not found"
                )

            # 3. Check availability
            availability = session.scalar(
                select(AvailabilityDB).where(
                    AvailabilityDB.employee_id
                    == request.employee_id,
                    AvailabilityDB.shift_id
                    == request.shift_id
                )
            )

            if (
                availability is None
                or availability.status != "flexible"
            ):
                raise ValueError(
                    "Employee must be flexible for this shift"
                )

            # 4. Prevent duplicate assignments
            existing_assignment = session.scalar(
                select(AssignmentDB).where(
                    AssignmentDB.employee_id
                    == request.employee_id,
                    AssignmentDB.shift_id
                    == request.shift_id
                )
            )

            if existing_assignment is not None:
                raise ValueError(
                    "Employee is already assigned"
                )

            # 5. Check shift capacity
            assigned_count = session.scalar(
                select(func.count())
                .select_from(AssignmentDB)
                .where(
                    AssignmentDB.shift_id == shift.shift_id
                )
            )

            if assigned_count >= shift.required_employees:
                raise ValueError(
                    "Shift is already fully staffed"
                )

            # 6. Check employee shift limit
            employee_assignments = session.scalars(
                select(AssignmentDB).where(
                    AssignmentDB.employee_id
                    == employee.employee_id
                )
            ).all()

            if len(employee_assignments) >= employee.max_shifts:
                raise ValueError(
                    "Employee reached maximum shifts"
                )

            # 7. Check overlapping shifts
            for assignment in employee_assignments:

                other_shift = session.get(
                    ShiftDB,
                    assignment.shift_id
                )

                if other_shift is None:
                    raise ValueError(
                        "Assigned shift not found"
                    )

                if other_shift.date != shift.date:
                    continue

                overlaps = (
                    shift.start_time < other_shift.end_time
                    and other_shift.start_time < shift.end_time
                )

                if overlaps:
                    raise ValueError(
                        "Employee has an overlapping shift"
                    )

            # 8. Update request and availability
            request.status = "accepted"
            availability.status = "available"

            # 9. Create the assignment
            session.add(
                AssignmentDB(
                    employee_id=request.employee_id,
                    shift_id=request.shift_id
                )
            )

            # The transaction commits automatically
            # if no exception occurs.

    return True

def decline_staffing_request(request_id, db_engine=None):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():
            request = session.get(
                StaffingRequestDB,
                request_id
            )

            if request is None:
                raise ValueError("Request not found")

            if request.status != "pending":
                raise ValueError(
                    "Only pending requests can be declined"
                )

            request.status = "declined"

    return True

