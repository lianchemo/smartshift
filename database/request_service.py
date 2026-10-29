
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import (
    StaffingRequestDB,
    AvailabilityDB
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
