
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus
from scheduler import generate_schedule


def test_unavailable_employee_is_not_assigned():
    # Arrange: create employee, shift, and availability
    employee = Employee(101, "Dana", 4, 3)

    shift = Shift(
        201,
        date(2026, 11, 1),
        time(8, 0),
        time(16, 0),
        1
    )

    availability = Availability(
        101,
        201,
        AvailabilityStatus.UNAVAILABLE
    )

    # Act: generate the schedule
    assignments = generate_schedule(
        [employee],
        [shift],
        [availability]
    )

    # Assert: unavailable employee must not be assigned
    assert len(assignments) == 0


def test_flexible_employee_is_not_assigned():
    employee = Employee(102, "Noa", 5, 4)

    shift = Shift(
        202,
        date(2026, 11, 1),
        time(16, 0),
        time(23, 0),
        1
    )

    availability = Availability(
        102,
        202,
        AvailabilityStatus.FLEXIBLE
    )

    assignments = generate_schedule(
        [employee],
        [shift],
        [availability]
    )

    assert len(assignments) == 0

def test_available_employee_is_assigned():
    employee = Employee(103, "Maya", 4, 3)

    shift = Shift(
        203,
        date(2026, 11, 2),
        time(8, 0),
        time(16, 0),
        1
    )

    availability = Availability(
        103,
        203,
        AvailabilityStatus.AVAILABLE
    )

    assignments = generate_schedule(
        [employee],
        [shift],
        [availability]
    )

    assert len(assignments) == 1
    assert assignments[0].employee_id == 103
    assert assignments[0].shift_id == 203


def test_employee_cannot_be_assigned_to_overlapping_shifts():
    # Arrange
    employee = Employee(101, "Dana", 4, 3)

    shift1 = Shift(
        201,
        date(2026, 11, 1),
        time(8, 0),
        time(16, 0),
        1
    )

    shift2 = Shift(
        202,
        date(2026, 11, 1),
        time(14, 0),
        time(20, 0),
        1
    )

    availabilities = [
        Availability(101, 201, AvailabilityStatus.AVAILABLE),
        Availability(101, 202, AvailabilityStatus.AVAILABLE)
    ]

    # Act
    assignments = generate_schedule(
        [employee],
        [shift1, shift2],
        availabilities
    )

    # Assert
    assert len(assignments) == 1
    assert assignments[0].shift_id == 201


def test_employee_does_not_exceed_max_shifts():
    # Arrange
    employee = Employee(101, "Dana", 2, 2)

    shifts = [
        Shift(201, date(2026, 11, 1), time(8, 0), time(16, 0), 1),
        Shift(202, date(2026, 11, 2), time(8, 0), time(16, 0), 1),
        Shift(203, date(2026, 11, 3), time(8, 0), time(16, 0), 1)
    ]

    availabilities = [
        Availability(101, 201, AvailabilityStatus.AVAILABLE),
        Availability(101, 202, AvailabilityStatus.AVAILABLE),
        Availability(101, 203, AvailabilityStatus.AVAILABLE)
    ]

    # Act
    assignments = generate_schedule(
        [employee],
        shifts,
        availabilities
    )

    # Assert
    assert len(assignments) == 2

    assigned_shift_ids = {
        assignment.shift_id
        for assignment in assignments
    }

    assert assigned_shift_ids == {201, 202}



