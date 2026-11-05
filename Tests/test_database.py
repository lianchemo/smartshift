from database.availability_repository import save_employee_availability
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


def test_approve_weekly_schedule_rejects_stale_preview():
    import pytest

    from database.weekly_schedule_service import (
        generate_weekly_schedule_preview,
        approve_weekly_schedule
    )
    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB,
        AssignmentDB
    )

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    week_start = date(2026, 11, 8)

    with Session(test_engine) as session:
        with session.begin():
            session.add(
                EmployeeDB(
                    employee_id=999,
                    name="Test Employee",
                    max_shifts=3,
                    preferred_shifts=2
                )
            )

            session.add(
                ShiftDB(
                    shift_id=901,
                    date=week_start,
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                    required_employees=1
                )
            )

            session.add(
                AvailabilityDB(
                    employee_id=999,
                    shift_id=901,
                    status="available"
                )
            )

    preview = generate_weekly_schedule_preview(
        week_start=week_start,
        db_engine=test_engine
    )

    assert len(preview) == 1

    # The employee changes availability after preview.
    with Session(test_engine) as session:
        with session.begin():
            availability = session.scalar(
                select(AvailabilityDB).where(
                    AvailabilityDB.employee_id == 999,
                    AvailabilityDB.shift_id == 901
                )
            )

            availability.status = "unavailable"

    # The manager tries to approve the old preview.
    with pytest.raises(
        ValueError,
        match="Schedule has changed"
    ):
        approve_weekly_schedule(
            week_start=week_start,
            expected_new_assignments=preview,
            db_engine=test_engine
        )

    # Nothing should have been saved.
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB)
        ).all()

        assert len(saved_assignments) == 0

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


def test_weekly_preview_handles_empty_database():
    from database.weekly_schedule_service import (
        generate_weekly_schedule_preview
    )

    # Create an empty temporary database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    # Generate a preview from the empty database
    preview = generate_weekly_schedule_preview(
        db_engine=test_engine
    )

    # No employees or shifts = no assignments
    assert preview == []

    # Verify nothing was saved
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB)
        ).all()

        assert len(saved_assignments) == 0


def test_weekly_preview_proposes_assignment_without_saving():
    from database.weekly_schedule_service import (
        generate_weekly_schedule_preview
    )

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
                required_employees=1
            )
        )

        session.add(
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="available"
            )
        )

        session.commit()

    # Generate a proposal
    preview = generate_weekly_schedule_preview(
        db_engine=test_engine
    )

    # The preview should propose Roni
    assert len(preview) == 1
    assert preview[0].employee_id == 107
    assert preview[0].shift_id == 213

    # Verify that SQLite remains unchanged
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB)
        ).all()

        assert len(saved_assignments) == 0

def test_weekly_preview_only_includes_selected_week():
    from database.weekly_schedule_service import (
        generate_weekly_schedule_preview
    )

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

        # First week: November 1-7
        session.add(
            ShiftDB(
                shift_id=213,
                date=date(2026, 11, 7),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
        )

        # Second week: November 8-14
        session.add(
            ShiftDB(
                shift_id=300,
                date=date(2026, 11, 8),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
        )

        session.add_all([
            AvailabilityDB(
                employee_id=107,
                shift_id=213,
                status="available"
            ),
            AvailabilityDB(
                employee_id=107,
                shift_id=300,
                status="available"
            )
        ])

        session.commit()

    # Generate schedule for the first week only
    preview = generate_weekly_schedule_preview(
        week_start=date(2026, 11, 1),
        db_engine=test_engine
    )

    assert len(preview) == 1
    assert preview[0].shift_id == 213

    # Generate schedule for the second week only
    second_preview = generate_weekly_schedule_preview(
        week_start=date(2026, 11, 8),
        db_engine=test_engine
    )

    assert len(second_preview) == 1
    assert second_preview[0].shift_id == 300

def test_employee_can_submit_new_availability():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    # Create an employee and a shift
    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=102,
                name="Noa",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=300,
                date=date(2026, 11, 8),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
        )

        session.commit()

    # Noa submits her availability
    save_employee_availability(
        employee_id=102,
        shift_id=300,
        new_status="available",
        db_engine=test_engine
    )

    # Check that SQLite saved the new record
    with Session(test_engine) as session:
        saved_availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 102,
                AvailabilityDB.shift_id == 300
            )
        )

        assert saved_availability is not None
        assert saved_availability.status == "available"

def test_employee_can_update_existing_availability():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    # Create employee, shift and existing availability
    with Session(test_engine) as session:
        session.add(
            EmployeeDB(
                employee_id=102,
                name="Noa",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        session.add(
            ShiftDB(
                shift_id=300,
                date=date(2026, 11, 8),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
        )

        session.add(
            AvailabilityDB(
                employee_id=102,
                shift_id=300,
                status="flexible"
            )
        )

        session.commit()

    # Noa changes her availability to available
    save_employee_availability(
        employee_id=102,
        shift_id=300,
        new_status="available",
        db_engine=test_engine
    )

    # Check the updated status and prevent duplicates
    with Session(test_engine) as session:
        saved_records = session.scalars(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 102,
                AvailabilityDB.shift_id == 300
            )
        ).all()

        assert len(saved_records) == 1
        assert saved_records[0].status == "available"

def test_employee_cannot_change_availability_when_assigned():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Create employee
        session.add(
            EmployeeDB(
                employee_id=102,
                name="Noa",
                max_shifts=5,
                preferred_shifts=4
            )
        )

        # Create shift
        session.add(
            ShiftDB(
                shift_id=300,
                date=date(2026, 11, 8),
                start_time=time(8, 0),
                end_time=time(16, 0),
                required_employees=1
            )
        )

        # Noa is available for this shift
        session.add(
            AvailabilityDB(
                employee_id=102,
                shift_id=300,
                status="available"
            )
        )

        # Noa is already assigned to the shift
        session.add(
            AssignmentDB(
                employee_id=102,
                shift_id=300
            )
        )

        session.commit()

    # Attempt to change availability after assignment
    with pytest.raises(
        ValueError,
        match="Cannot change availability for an assigned shift"
    ):
        save_employee_availability(
            employee_id=102,
            shift_id=300,
            new_status="unavailable",
            db_engine=test_engine
        )

    # Verify that the original data remains unchanged
    with Session(test_engine) as session:
        availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 102,
                AvailabilityDB.shift_id == 300
            )
        )

        assignment = session.scalar(
            select(AssignmentDB).where(
                AssignmentDB.employee_id == 102,
                AssignmentDB.shift_id == 300
            )
        )

        assert availability.status == "available"
        assert assignment is not None

def test_create_weekly_shifts_without_duplicates():
    from database.weekly_shift_service import (
        create_weekly_shifts
    )

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    # First run: create all 14 shifts.
    first_count = create_weekly_shifts(
        week_start=date(2026, 11, 8),
        required_employees=2,
        db_engine=test_engine
    )

    assert first_count == 14

    # Second run: do not create duplicates.
    second_count = create_weekly_shifts(
        week_start=date(2026, 11, 8),
        required_employees=2,
        db_engine=test_engine
    )

    assert second_count == 0

    with Session(test_engine) as session:
        saved_shifts = session.scalars(
            select(ShiftDB)
        ).all()

        assert len(saved_shifts) == 14

def test_weekly_shifts_support_different_staffing_requirements():
    from database.weekly_shift_service import create_weekly_shifts

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    staffing_requirements = [
        2, 3,  # Sunday
        2, 3,  # Monday
        2, 3,  # Tuesday
        2, 3,  # Wednesday
        2, 3,  # Thursday
        4, 5,  # Friday
        5, 6   # Saturday
    ]

    created_count = create_weekly_shifts(
        week_start=date(2026, 11, 8),
        staffing_requirements=staffing_requirements,
        db_engine=test_engine
    )

    assert created_count == 14

    with Session(test_engine) as session:
        saved_shifts = session.scalars(
            select(ShiftDB).order_by(
                ShiftDB.date,
                ShiftDB.start_time
            )
        ).all()

        assert len(saved_shifts) == 14

        saved_requirements = [
            shift.required_employees
            for shift in saved_shifts
        ]

        assert saved_requirements == staffing_requirements

        # Friday evening needs 5 employees
        assert saved_shifts[11].required_employees == 5

        # Saturday evening needs 6 employees
        assert saved_shifts[13].required_employees == 6

def test_save_weekly_availability_is_atomic():
    import pytest

    from database.availability_repository import (
        save_weekly_availability
    )
    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB
    )

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        with session.begin():
            session.add(
                EmployeeDB(
                    employee_id=999,
                    name="Test Employee",
                    max_shifts=5,
                    preferred_shifts=3
                )
            )

            session.add_all([
                ShiftDB(
                    shift_id=901,
                    date=date(2026, 11, 8),
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                    required_employees=2
                ),
                ShiftDB(
                    shift_id=902,
                    date=date(2026, 11, 8),
                    start_time=time(16, 0),
                    end_time=time(23, 0),
                    required_employees=2
                ),
                ShiftDB(
                    shift_id=903,
                    date=date(2026, 11, 9),
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                    required_employees=2
                )
            ])

    # Successful submission: all three choices are saved.
    saved_count = save_weekly_availability(
        employee_id=999,
        shift_statuses={
            901: "available",
            902: "flexible",
            903: "unavailable"
        },
        db_engine=test_engine
    )

    assert saved_count == 3

    with Session(test_engine) as session:
        saved_rows = session.scalars(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 999
            )
        ).all()

        assert len(saved_rows) == 3

    # Failed submission: shift 9999 does not exist.
    with pytest.raises(ValueError):
        save_weekly_availability(
            employee_id=999,
            shift_statuses={
                901: "unavailable",
                9999: "available"
            },
            db_engine=test_engine
        )

    # Check that the attempted change to shift 901
    # was also rolled back.
    with Session(test_engine) as session:
        shift_901_availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 999,
                AvailabilityDB.shift_id == 901
            )
        )

        assert shift_901_availability.status == "available"

def test_weekly_deadline_save_and_update():
    import pytest

    from datetime import time, datetime

    from database.weekly_deadline_repository import (
        save_weekly_deadline,
        get_weekly_deadline
    )
    from database.models import WeeklyDeadlineDB

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    week_start = date(2026, 11, 15)

    # Save the first deadline.
    save_weekly_deadline(
        week_start=week_start,
        deadline_date=date(2026, 11, 12),
        deadline_time=time(20, 0),
        db_engine=test_engine
    )

    assert get_weekly_deadline(
        week_start,
        db_engine=test_engine
    ) == datetime(2026, 11, 12, 20, 0)

    # Update the existing deadline.
    save_weekly_deadline(
        week_start=week_start,
        deadline_date=date(2026, 11, 13),
        deadline_time=time(18, 30),
        db_engine=test_engine
    )

    assert get_weekly_deadline(
        week_start,
        db_engine=test_engine
    ) == datetime(2026, 11, 13, 18, 30)

    # The update must not create a duplicate row.
    with Session(test_engine) as session:
        deadlines = session.scalars(
            select(WeeklyDeadlineDB)
        ).all()

        assert len(deadlines) == 1

    # Reject a deadline on or after Sunday.
    with pytest.raises(ValueError):
        save_weekly_deadline(
            week_start=week_start,
            deadline_date=date(2026, 11, 15),
            deadline_time=time(10, 0),
            db_engine=test_engine
        )

    # Invalid input must not change the saved deadline.
    assert get_weekly_deadline(
        week_start,
        db_engine=test_engine
    ) == datetime(2026, 11, 13, 18, 30)

def test_weekly_availability_blocked_after_deadline():
    import pytest

    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from database.availability_repository import (
        save_weekly_availability
    )
    from database.models import (
        EmployeeDB,
        ShiftDB,
        WeeklyDeadlineDB,
        AvailabilityDB
    )

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    israel_now = datetime.now(ZoneInfo("Asia/Jerusalem"))

    # Use a Sunday in the past, so its deadline has passed.
    days_since_sunday = (israel_now.weekday() + 1) % 7
    week_start = (
        israel_now.date()
        - timedelta(days=days_since_sunday + 14)
    )

    past_deadline = (
        datetime.combine(
            week_start - timedelta(days=2),
            time(20, 0)
        )
    )

    with Session(test_engine) as session:
        with session.begin():
            session.add(
                EmployeeDB(
                    employee_id=999,
                    name="Test Employee",
                    max_shifts=5,
                    preferred_shifts=3
                )
            )

            session.add(
                ShiftDB(
                    shift_id=901,
                    date=week_start,
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                    required_employees=2
                )
            )

            session.add(
                WeeklyDeadlineDB(
                    week_start=week_start,
                    deadline_at=past_deadline
                )
            )

    # Saving after the deadline must be rejected.
    with pytest.raises(
        ValueError,
        match="deadline has passed"
    ):
        save_weekly_availability(
            employee_id=999,
            shift_statuses={
                901: "available"
            },
            db_engine=test_engine
        )

    # Confirm that nothing was saved.
    with Session(test_engine) as session:
        saved_availability = session.scalar(
            select(AvailabilityDB).where(
                AvailabilityDB.employee_id == 999,
                AvailabilityDB.shift_id == 901
            )
        )

        assert saved_availability is None

def test_approve_weekly_schedule_saves_assignments():
    from database.weekly_schedule_service import (
        generate_weekly_schedule_preview,
        approve_weekly_schedule
    )
    from database.models import (
        EmployeeDB,
        ShiftDB,
        AvailabilityDB,
        AssignmentDB,
        WeeklyScheduleDB
    )

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    week_start = date(2026, 11, 8)

    with Session(test_engine) as session:
        with session.begin():
            session.add(
                EmployeeDB(
                    employee_id=999,
                    name="Test Employee",
                    max_shifts=3,
                    preferred_shifts=2
                )
            )

            session.add(
                ShiftDB(
                    shift_id=901,
                    date=week_start,
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                    required_employees=1
                )
            )

            session.add(
                AvailabilityDB(
                    employee_id=999,
                    shift_id=901,
                    status="available"
                )
            )

    # Generate the preview.
    preview = generate_weekly_schedule_preview(
        week_start=week_start,
        db_engine=test_engine
    )

    assert len(preview) == 1

    # Approve the proposed assignment.
    saved_count = approve_weekly_schedule(
        week_start=week_start,
        expected_new_assignments=preview,
        db_engine=test_engine
    )

    assert saved_count == 1

    # Verify the assignment was actually saved.
    with Session(test_engine) as session:
        saved_assignments = session.scalars(
            select(AssignmentDB)
        ).all()

        assert len(saved_assignments) == 1
        assert saved_assignments[0].employee_id == 999
        assert saved_assignments[0].shift_id == 901
        # The schedule must be approved too.
        weekly_schedule = session.get(
            WeeklyScheduleDB,
            week_start
        )

        assert weekly_schedule is not None
        assert weekly_schedule.status == "approved"

def test_weekly_schedule_approval_and_publication():
    import pytest

    from database.weekly_schedule_status_repository import (
        get_weekly_schedule_status,
        mark_weekly_schedule_approved,
        publish_weekly_schedule
    )
    from database.models import WeeklyScheduleDB

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)

    week_start = date(2026, 11, 15)

    # A week without a saved status is a draft.
    assert get_weekly_schedule_status(
        week_start,
        db_engine=test_engine
    ) == "draft"

    # A draft cannot be published directly.
    with pytest.raises(
        ValueError,
        match="approved before publishing"
    ):
        publish_weekly_schedule(
            week_start,
            db_engine=test_engine
        )

    # Mark the week as approved.
    mark_weekly_schedule_approved(
        week_start,
        db_engine=test_engine
    )

    assert get_weekly_schedule_status(
        week_start,
        db_engine=test_engine
    ) == "approved"

    # Publish the approved schedule.
    publish_weekly_schedule(
        week_start,
        db_engine=test_engine
    )

    assert get_weekly_schedule_status(
        week_start,
        db_engine=test_engine
    ) == "published"

    # Check that the publication date was saved.
    with Session(test_engine) as session:
        schedule = session.get(
            WeeklyScheduleDB,
            week_start
        )

        assert schedule.published_at is not None

    # A published schedule cannot be approved again.
    with pytest.raises(
        ValueError,
        match="cannot be approved again"
    ):
        mark_weekly_schedule_approved(
            week_start,
            db_engine=test_engine
        )

















