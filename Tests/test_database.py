from database.models import StaffingRequestDB
from database.request_service import approve_staffing_request
from database.availability_repository import update_availability
import pytest

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from database.models import AvailabilityDB
from datetime import date, time
from database.models import ShiftDB
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.models import Base, EmployeeDB


def test_employee_can_be_saved_and_loaded():
    # Arrange: create a temporary in-memory database
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    # Act: save an employee
    with Session(engine) as session:
        employee = EmployeeDB(
            employee_id=101,
            name="Dana",
            max_shifts=4,
            preferred_shifts=3
        )

        session.add(employee)
        session.commit()

    # Act: load the employee from the database
    with Session(engine) as session:
        statement = select(EmployeeDB).where(
            EmployeeDB.employee_id == 101
        )

        saved_employee = session.scalar(statement)

        # Assert
        assert saved_employee is not None
        assert saved_employee.name == "Dana"
        assert saved_employee.max_shifts == 4
        assert saved_employee.preferred_shifts == 3


def test_shift_can_be_saved_and_loaded():
    # Arrange: create a temporary database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Act: save a shift
    with Session(engine) as session:
        shift = ShiftDB(
            shift_id=201,
            date=date(2026, 11, 1),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=2
        )

        session.add(shift)
        session.commit()

    # Act: load the shift in a new session
    with Session(engine) as session:
        saved_shift = session.get(ShiftDB, 201)

        # Assert
        assert saved_shift is not None
        assert saved_shift.date == date(2026, 11, 1)
        assert saved_shift.start_time == time(8, 0)
        assert saved_shift.end_time == time(16, 0)
        assert saved_shift.required_employees == 2


def test_availability_requires_existing_employee():
    # Create a temporary database
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key enforcement for this engine
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, connection_record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    # Create a valid shift, but no employee with ID 999
    with Session(engine) as session:
        shift = ShiftDB(
            shift_id=201,
            date=date(2026, 11, 1),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=2
        )

        session.add(shift)
        session.commit()

    # Try to save availability for a nonexistent employee
    with Session(engine) as session:
        availability = AvailabilityDB(
            employee_id=999,
            shift_id=201,
            status="available"
        )

        session.add(availability)

        with pytest.raises(IntegrityError):
            session.commit()

def test_availability_can_be_updated():
    # Arrange - temporary database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="flexible"
            )
        )

        session.commit()

    # Act
    update_availability(
        107,
        213,
        "available",
        db_engine=test_engine
    )

    # Assert
    with Session(test_engine) as session:
        saved_availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        assert saved_availability is not None
        assert saved_availability.status == "available"

def test_approve_request_updates_request_and_availability():
    # Arrange: temporary database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="flexible"
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="pending"
            )
        )

        session.commit()

    # Act
    approve_staffing_request(
        1,
        db_engine=test_engine
    )

    # Assert: verify both changes were saved
    with Session(test_engine) as session:
        saved_request = session.get(
            StaffingRequestDB,
            1
        )

        saved_availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        assert saved_request.status == "accepted"
        assert saved_availability.status == "available"

def test_approval_fails_without_availability():
    # Arrange: create a temporary database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="pending"
            )
        )

        session.commit()

    # Act: approval should fail
    with pytest.raises(
        ValueError,
        match="Availability record not found"
    ):
        approve_staffing_request(
            1,
            db_engine=test_engine
        )

    # Assert: request status must remain pending
    with Session(test_engine) as session:
        saved_request = session.get(
            StaffingRequestDB,
            1
        )

        assert saved_request.status == "pending"

def test_transaction_rolls_back_after_error():
    # Arrange: create a temporary database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="pending"
            )
        )

        session.commit()

    # Act: change data, then simulate a failure
    with pytest.raises(RuntimeError):
        with Session(test_engine) as session:
            with session.begin():
                request = session.get(
                    StaffingRequestDB, 1
                )

                request.status = "accepted"

                # Force the change to reach the database
                # without committing the transaction
                session.flush()

                raise RuntimeError("Simulated failure")

    # Assert: the change was rolled back
    with Session(test_engine) as session:
        saved_request = session.get(
            StaffingRequestDB, 1
        )

        assert saved_request.status == "pending"






