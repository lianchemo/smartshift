
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
