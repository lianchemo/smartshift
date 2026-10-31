
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.models import (
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    StaffingRequestDB
)


demo_path = Path(__file__).resolve().parent / "smartshift_demo.db"

if not demo_path.is_file():
    raise RuntimeError("Demo database not found")


demo_engine = create_engine(
    f"sqlite:///{demo_path.as_posix()}"
)

with Session(demo_engine) as session:
    with session.begin():

        employee = session.get(EmployeeDB, 102)

        if employee is None:
            raise RuntimeError("Noa was not found")

        # Create a separate test shift
        shift = session.get(ShiftDB, 300)

        if shift is None:
            from datetime import date, time

            shift = ShiftDB(
                shift_id=300,
                date=date(2026, 11, 8),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
            session.add(shift)

        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 102,
                AvailabilityDB.shift_id == 300
            )
        )

        if availability is None:
            session.add(
                AvailabilityDB(
                    employee_id=102,
                    shift_id=300,
                    status="flexible"
                )
            )

        existing_request = session.scalar(
            select(StaffingRequestDB).where(
                StaffingRequestDB.employee_id == 102,
                StaffingRequestDB.shift_id == 300
            )
        )

        if existing_request is None:
            session.add(
                StaffingRequestDB(
                    employee_id=102,
                    shift_id=300,
                    status="pending"
                )
            )

print("Decline demo scenario is ready!")
print("Noa has a pending request for shift 300.")
