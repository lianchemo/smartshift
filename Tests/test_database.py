from database.assignment_service import assign_accepted_request
from database.models import AssignmentDB
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

def test_accepted_request_creates_assignment():
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
                status="available"
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="accepted"
            )
        )

        session.commit()

    assign_accepted_request(
        1,
        db_engine=test_engine
    )

    with Session(test_engine) as session:
        saved_assignment = session.scalar(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107,
                AssignmentDB.shift_id == 213
            )
        )

        assert saved_assignment is not None

def test_accepted_request_cannot_create_duplicate_assignment():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    # Arrange: create an already assigned employee
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
                status="available"
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="accepted"
            )
        )

        # Roni is already assigned to this shift
        session.add(
            AssignmentDB(
                employee_id=107,
                shift_id=213
            )
        )

        session.commit()

    # Act: try to assign Roni again
    with pytest.raises(
        ValueError,
        match="Employee is already assigned"
    ):
        assign_accepted_request(
            1,
            db_engine=test_engine
        )

    # Assert: only one assignment exists
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107,
                AssignmentDB.shift_id == 213
            )
        ).all()

        assert len(saved_assignments) == 1

def test_accepted_request_cannot_fill_full_shift():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Create employees
        session.add_all([
            EmployeeDB(
                employee_id=101,
                name="Dana",
                max_shifts=5,
                preferred_shifts=4
            ),
            EmployeeDB(
                employee_id=102,
                name="Noa",
                max_shifts=5,
                preferred_shifts=4
            ),
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        ])

        # Shift requires only two employees
        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        # The shift is already full
        session.add_all([
            AssignmentDB(
                employee_id=101,
                shift_id=213
            ),
            AssignmentDB(
                employee_id=102,
                shift_id=213
            )
        ])

        # Roni is available and has accepted
        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="available"
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="accepted"
            )
        )

        session.commit()

    # Attempt to assign a third employee
    with pytest.raises(
        ValueError,
        match="Shift is already fully staffed"
    ):
        assign_accepted_request(
            1,
            db_engine=test_engine
        )

    # The shift must still have exactly two employees
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.shift_id == 213
            )
        ).all()

        assert len(saved_assignments) == 2

        assert all(
            assignment.employee_id != 107
            for assignment in saved_assignments
        )

def test_accepted_request_cannot_create_overlapping_shifts():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Create employee
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        # Existing shift: 08:00–16:00
        session.add(
            ShiftDB(
                shift_id=211,
                date=date(2026, 11, 6),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        # Requested shift: 14:00–22:00
        session.add(
            ShiftDB(
                shift_id=215,
                date=date(2026, 11, 6),
                start_time=time(14, 0),
                end_time=time(22, 0),
                required_employees=2
            )
        )

        # Roni is already assigned to shift 211
        session.add(
            AssignmentDB(
                employee_id=107,
                shift_id=211
            )
        )

        # Roni is available for shift 215
        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=215,
                status="available"
            )
        )

        # Accepted request for shift 215
        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=215,
                status="accepted"
            )
        )

        session.commit()

    # Attempt to assign overlapping shift
    with pytest.raises(
        ValueError,
        match="Employee has an overlapping shift"
    ):
        assign_accepted_request(
            1,
            db_engine=test_engine
        )

    # Verify no new assignment was saved
    with Session(test_engine) as session:
        assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107
            )
        ).all()

        assert len(assignments) == 1
        assert assignments[0].shift_id == 211

def test_accepted_request_respects_max_shifts():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Roni can work a maximum of 2 shifts
        session.add(
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=2,
                preferred_shifts=2
            )
        )

        # Three non-overlapping shifts
        session.add_all([
            ShiftDB(
                shift_id=211,
                date=date(2026, 11, 5),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            ),
            ShiftDB(
                shift_id=212,
                date=date(2026, 11, 6),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            ),
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        ])

        # Roni already has two assignments
        session.add_all([
            AssignmentDB(
                employee_id=107,
                shift_id=211
            ),
            AssignmentDB(
                employee_id=107,
                shift_id=212
            )
        ])

        # Roni accepted a third shift
        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="available"
            )
        )

        session.add(
            StaffingRequestDB(
                request_id=1,
                employee_id=107,
                shift_id=213,
                status="accepted"
            )
        )

        session.commit()

    # Attempt to exceed the shift limit
    with pytest.raises(
        ValueError,
        match="Employee reached maximum shifts"
    ):
        assign_accepted_request(
            1,
            db_engine=test_engine
        )

    # Verify only the original two assignments exist
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107
            )
        ).all()

        assert len(saved_assignments) == 2

        assert {
            assignment.shift_id
            for assignment in saved_assignments
        } == {211, 212}

def test_approval_and_assignment_should_be_atomic():
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

    # Import the combined service we will implement next
    from database.request_service import (
        accept_and_assign_request
    )

    accept_and_assign_request(
        1,
        db_engine=test_engine
    )

    with Session(test_engine) as session:
        request = session.get(StaffingRequestDB, 1)

        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        assignment = session.scalar(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107,
                AssignmentDB.shift_id == 213
            )
        )

        assert request.status == "accepted"
        assert availability.status == "available"
        assert assignment is not None

def test_accept_and_assign_keeps_data_unchanged_when_shift_full():
    from database.request_service import accept_and_assign_request

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        session.add_all([
            EmployeeDB(
                employee_id=101,
                name="Dana",
                max_shifts=5,
                preferred_shifts=4
            ),
            EmployeeDB(
                employee_id=102,
                name="Noa",
                max_shifts=5,
                preferred_shifts=4
            ),
            EmployeeDB(
                employee_id=107,
                name="Roni",
                max_shifts=5,
                preferred_shifts=4
            )
        ])

        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=2
            )
        )

        # The shift already has two employees
        session.add_all([
            AssignmentDB(
                employee_id=101,
                shift_id=213
            ),
            AssignmentDB(
                employee_id=102,
                shift_id=213
            )
        ])

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

    # Trying to accept must fail
    with pytest.raises(
        ValueError,
        match="Shift is already fully staffed"
    ):
        accept_and_assign_request(
            1,
            db_engine=test_engine
        )

    # Verify nothing was changed
    with Session(test_engine) as session:
        request = session.get(StaffingRequestDB, 1)

        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.shift_id == 213
            )
        ).all()

        assert request.status == "pending"
        assert availability.status == "flexible"
        assert len(assignments) == 2

        assert 107 not in {
            assignment.employee_id
            for assignment in assignments
        }

def test_decline_request_keeps_availability_and_assignments():
    from database.request_service import decline_staffing_request

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

    decline_staffing_request(1, db_engine=test_engine)

    with Session(test_engine) as session:
        request = session.get(StaffingRequestDB, 1)

        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 107,
                AvailabilityDB.shift_id == 213
            )
        )

        assignments = session.scalars(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 107,
                AssignmentDB.shift_id == 213
            )
        ).all()

        assert request.status == "declined"
        assert availability.status == "flexible"
        assert len(assignments) == 0











