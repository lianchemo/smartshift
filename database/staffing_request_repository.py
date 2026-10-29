
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import StaffingRequestDB


def add_staffing_request(employee_id, shift_id):
    with Session(engine) as session:
        # Prevent multiple pending requests for the same employee and shift
        statement = select(StaffingRequestDB).where(
            StaffingRequestDB.employee_id == employee_id,
            StaffingRequestDB.shift_id == shift_id,
            StaffingRequestDB.status == "pending"
        )

        existing_request = session.scalar(statement)

        if existing_request is not None:
            print("A pending request already exists.")
            return existing_request.request_id

        request = StaffingRequestDB(
            employee_id=employee_id,
            shift_id=shift_id,
            status="pending"
        )

        session.add(request)
        session.commit()

        request_id = request.request_id

        print(f"Staffing request {request_id} saved!")
        return request_id


def get_all_staffing_requests():
    with Session(engine) as session:
        statement = select(StaffingRequestDB).order_by(
            StaffingRequestDB.request_id
        )

        return session.scalars(statement).all()

def update_request_status(request_id, new_status):
    valid_statuses = {"accepted", "declined"}

    if new_status not in valid_statuses:
        raise ValueError("Invalid request status")

    with Session(engine) as session:
        request = session.get(StaffingRequestDB, request_id)

        if request is None:
            raise ValueError("Staffing request not found")

        if request.status != "pending":
            raise ValueError("Only pending requests can be updated")

        request.status = new_status
        session.commit()

        print(
            f"Request {request_id} updated to {new_status}"
        )
