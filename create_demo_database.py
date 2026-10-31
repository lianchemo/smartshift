
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.models import (
    Base,
    EmployeeDB,
    ShiftDB,
    AvailabilityDB,
    AssignmentDB,
    StaffingRequestDB
)

from database.db import engine as original_engine


# Separate database for the interactive demo
demo_path = Path(__file__).resolve().parent / "smartshift_demo.db"

demo_engine = create_engine(
    f"sqlite:///{demo_path.as_posix()}"
)

Base.metadata.create_all(demo_engine)

# Safety check: do not overwrite an existing demo database
with Session(demo_engine) as session:
    existing_employees = session.scalar(
        select(EmployeeDB.employee_id).limit(1)
    )

    if existing_employees is not None:
        raise RuntimeError(
            "Demo database already contains data. "
            "Nothing was changed."
        )


# Copy current data into the new demo database
with Session(original_engine) as source:
    with Session(demo_engine) as target:

        for row in source.scalars(select(EmployeeDB)):
            target.add(
                EmployeeDB(
                    employee_id=row.employee_id,
                    name=row.name,
                    max_shifts=row.max_shifts,
                    preferred_shifts=row.preferred_shifts
                )
            )

        for row in source.scalars(select(ShiftDB)):
            target.add(
                ShiftDB(
                    shift_id=row.shift_id,
                    date=row.date,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    required_employees=row.required_employees
                )
            )

        target.flush()

        for row in source.scalars(select(AvailabilityDB)):
            target.add(
                AvailabilityDB(
                    employee_id=row.employee_id,
                    shift_id=row.shift_id,
                    status=row.status
                )
            )

        for row in source.scalars(select(AssignmentDB)):
            target.add(
                AssignmentDB(
                    employee_id=row.employee_id,
                    shift_id=row.shift_id
                )
            )

        for row in source.scalars(select(StaffingRequestDB)):
            target.add(
                StaffingRequestDB(
                    employee_id=row.employee_id,
                    shift_id=row.shift_id,
                    status=row.status
                )
            )

        target.commit()


print("Demo database created successfully!")
print("Original database was not modified.")
