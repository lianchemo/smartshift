
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus
from scheduler import generate_schedule
from assignment import Assignment


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

def test_existing_assignments_are_preserved():
    # Arrange
    employee1 = Employee(101, "Dana", 2, 2)
    employee2 = Employee(102, "Noa", 2, 2)

    shift = Shift(
        201,
        date(2026, 11, 1),
        time(8, 0),
        time(16, 0),
        2
    )

    availabilities = [
        Availability(101, 201, AvailabilityStatus.AVAILABLE),
        Availability(102, 201, AvailabilityStatus.AVAILABLE)
    ]

    existing_assignments = [
        Assignment(102, 201)
    ]

    # Act
    updated_assignments = generate_schedule(
        [employee1, employee2],
        [shift],
        availabilities,
        existing_assignments=existing_assignments
    )

    # Assert
    assert len(updated_assignments) == 2

    assignment_pairs = {
        (a.employee_id, a.shift_id)
        for a in updated_assignments
    }

    assert assignment_pairs == {
        (102, 201),
        (101, 201)
    }

def test_greedy_can_miss_full_schedule():
    from datetime import date, time

    from employee import Employee
    from shift import Shift
    from availability import (
        Availability,
        AvailabilityStatus
    )
    from scheduler import generate_schedule

    employees = [
        Employee(
            employee_id=101,
            name="Dana",
            max_shifts=1,
            preferred_shifts=1
        ),
        Employee(
            employee_id=102,
            name="Noa",
            max_shifts=1,
            preferred_shifts=1
        )
    ]

    shifts = [
        Shift(
            shift_id=201,
            shift_date=date(2026, 11, 8),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        ),
        Shift(
            shift_id=202,
            shift_date=date(2026, 11, 9),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
    ]

    availabilities = [
        Availability(
            employee_id=101,
            shift_id=201,
            status=AvailabilityStatus.AVAILABLE
        ),
        Availability(
            employee_id=101,
            shift_id=202,
            status=AvailabilityStatus.AVAILABLE
        ),
        Availability(
            employee_id=102,
            shift_id=201,
            status=AvailabilityStatus.AVAILABLE
        ),
        Availability(
            employee_id=102,
            shift_id=202,
            status=AvailabilityStatus.UNAVAILABLE
        )
    ]

    schedule = generate_schedule(
        employees,
        shifts,
        availabilities
    )

    assigned_pairs = {
        (assignment.employee_id, assignment.shift_id)
        for assignment in schedule
    }

    # A full schedule is possible:
    # Noa -> Sunday, Dana -> Monday.
    optimal_pairs = {
        (102, 201),
        (101, 202)
    }

    assert assigned_pairs == optimal_pairs

def test_schedule_distributes_shifts_fairly():
    from datetime import date, time

    from employee import Employee
    from shift import Shift
    from availability import Availability, AvailabilityStatus

    employees = [
        Employee(101, "Dana", 4, 4),
        Employee(102, "Noa", 4, 4),
        Employee(103, "Roni", 4, 4),
    ]

    shifts = [
        Shift(
            shift_id=201 + i,
            shift_date=date(2026, 11, 8 + i),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
        for i in range(4)
    ]

    availabilities = [
        Availability(
            employee_id=employee.employee_id,
            shift_id=shift.shift_id,
            status=AvailabilityStatus.AVAILABLE
        )
        for employee in employees
        for shift in shifts
    ]

    assignments = generate_schedule(
        employees, shifts, availabilities
    )

    counts = {
        employee.employee_id: sum(
            1
            for assignment in assignments
            if assignment.employee_id == employee.employee_id
        )
        for employee in employees
    }

    # All four shifts must be staffed.
    assert len(assignments) == 4

    # No employee should receive more than
    # one shift above another employee.
    assert max(counts.values()) - min(counts.values()) <= 1






