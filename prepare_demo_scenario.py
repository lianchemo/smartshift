
from pathlib import Path

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session

from database.models import (
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    AssignmentDB,
    StaffingRequestDB
)


# Work ONLY with the demo database
demo_path = Path(__file__).resolve().parent / "smartshift_demo.db"

if not demo_path.is_file():
    raise RuntimeError(
        "Demo database not found. Nothing was changed."
    )

demo_engine = create_engine(
    f"sqlite:///{demo_path.as_posix()}"
)


with Session(demo_engine) as session:
    with session.begin():

        # Ensure the expected demo data exists
        employee = session.get(EmployeeDB, 107)
        shift = session.get(ShiftDB, 213)

        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        request = session.scalar(
            select(StaffingRequestDB).where(
                StaffingRequestDB.employee_id == 107,
                StaffingRequestDB.shift_id == 213
            ).order_by(
                StaffingRequestDB.request_id
            ).limit(1)
        )

        if (
            employee is None
            or shift is None
            or availability is None
            or request is None
        ):
            raise RuntimeError(
                "Expected demo records are missing. "
                "Nothing was changed."
            )

        # Remove Roni's assignment in the DEMO only
        session.execute(
            delete(AssignmentDB).where(
                AssignmentDB.employee_id == 107,
                AssignmentDB.shift_id == 213
            )
        )

        # Return the demo request to pending
        request.status = "pending"

        # Return Roni's demo availability to flexible
        availability.status = "flexible"


print("Demo scenario prepared successfully!")
print("Roni's request is pending in the demo database.")
print("Original database was not modified.")
