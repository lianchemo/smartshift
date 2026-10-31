
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


with Session(engine) as session:
    request = session.get(StaffingRequestDB, 1)
    employee = session.get(EmployeeDB, 107)
    shift = session.get(ShiftDB, 213)

    availability = session.scalar(
        select(AvailabilityDB).where(
            AvailabilityDB.employee_id == 107,
            AvailabilityDB.shift_id == 213
        )
    )

    existing_assignment = session.scalar(
        select(AssignmentDB).where(
            AssignmentDB.employee_id == 107,
            AssignmentDB.shift_id == 213
        )
    )

    assigned_to_shift = session.scalar(
        select(func.count())
        .select_from(AssignmentDB)
        .where(AssignmentDB.shift_id == 213)
    )

    employee_assignments = session.scalars(
        select(AssignmentDB).where(
            AssignmentDB.employee_id == 107
        )
    ).all()

    print("Request:", request.status if request else None)
    print("Employee:", employee.name if employee else None)
    print("Shift:", shift.shift_id if shift else None)

    print(
        "Availability:",
        availability.status if availability else None
    )

    print(
        "Already assigned:",
        existing_assignment is not None
    )

    print(
        "Shift capacity:",
        f"{assigned_to_shift}/{shift.required_employees}"
        if shift else None
    )

    print(
        "Employee shifts:",
        f"{len(employee_assignments)}/{employee.max_shifts}"
        if employee else None
    )
