
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


def assign_accepted_request(request_id, db_engine=None):
    current_engine = db_engine if db_engine is not None else engine

    with Session(current_engine) as session:
        with session.begin():

            # Find the approved request
            request = session.get(
                StaffingRequestDB,
                request_id
            )

            if request is None:
                raise ValueError("Request not found")

            if request.status != "accepted":
                raise ValueError(
                    "Only accepted requests can be assigned"
                )

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

            # Verify the employee is available
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
                or availability.status != "available"
            ):
                raise ValueError(
                    "Employee is not available"
                )

            # Prevent duplicate assignments
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
                    "Employee is already assigned to this shift"
                )

            # Check remaining shift capacity
            assigned_to_shift = session.scalar(
                select(func.count()).select_from(
                    AssignmentDB
                ).where(
                    AssignmentDB.shift_id == shift.shift_id
                )
            )

            if assigned_to_shift >= shift.required_employees:
                raise ValueError(
                    "Shift is already fully staffed"
                )

            # Get all assignments for this employee
            employee_assignments = session.scalars(
                select(AssignmentDB).where(
                    AssignmentDB.employee_id
                    == employee.employee_id
                )
            ).all()

            # Check employee's shift limit
            if len(employee_assignments) >= employee.max_shifts:
                raise ValueError(
                    "Employee reached maximum shifts"
                )

            # Check overlapping shifts
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

            # All checks passed: save assignment
            new_assignment = AssignmentDB(
                employee_id=request.employee_id,
                shift_id=request.shift_id
            )

            session.add(new_assignment)

    return True
