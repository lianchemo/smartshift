
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus
from optimizer import optimize_schedule
from validation import validate_schedule


def test_optimizer_fills_all_possible_shifts():
    employees = [
        Employee(101, "Dana", 1, 1),
        Employee(102, "Noa", 1, 1),
        Employee(103, "Roni", 1, 1),
    ]

    shifts = [
        Shift(
            shift_id=301 + i,
            shift_date=date(2026, 11, 8 + i),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
        for i in range(3)
    ]

    availabilities = [
        Availability(101, 301, AvailabilityStatus.AVAILABLE),
        Availability(101, 302, AvailabilityStatus.AVAILABLE),
        Availability(101, 303, AvailabilityStatus.AVAILABLE),

        Availability(102, 301, AvailabilityStatus.AVAILABLE),
        Availability(102, 302, AvailabilityStatus.UNAVAILABLE),
        Availability(102, 303, AvailabilityStatus.UNAVAILABLE),

        Availability(103, 301, AvailabilityStatus.UNAVAILABLE),
        Availability(103, 302, AvailabilityStatus.AVAILABLE),
        Availability(103, 303, AvailabilityStatus.AVAILABLE),
    ]

    assignments = optimize_schedule(
        employees, shifts, availabilities
    )

    # All three shifts must be staffed.
    assert len(assignments) == 3

    # The schedule must satisfy all existing validation rules.
    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

    # Every shift must have an employee.
    assert {
        assignment.shift_id
        for assignment in assignments
    } == {301, 302, 303}

    # No employee can exceed one shift.
    assert len({
        assignment.employee_id
        for assignment in assignments
    }) == 3

def test_optimizer_preserves_existing_assignments():
    from assignment import Assignment

    employees = [
        Employee(101, "Dana", 1, 1),
        Employee(102, "Noa", 1, 1),
    ]

    shifts = [
        Shift(
            shift_id=301,
            shift_date=date(2026, 11, 8),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        ),
        Shift(
            shift_id=302,
            shift_date=date(2026, 11, 9),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
    ]

    availabilities = [
        Availability(101, 301, AvailabilityStatus.AVAILABLE),
        Availability(101, 302, AvailabilityStatus.AVAILABLE),
        Availability(102, 301, AvailabilityStatus.AVAILABLE),
        Availability(102, 302, AvailabilityStatus.AVAILABLE),
    ]

    # The manager already approved Dana for shift 302.
    existing_assignments = [
        Assignment(101, 302)
    ]

    assignments = optimize_schedule(
        employees,
        shifts,
        availabilities,
        existing_assignments=existing_assignments
    )

    assignment_pairs = {
        (a.employee_id, a.shift_id)
        for a in assignments
    }

    # Dana's approved assignment must remain unchanged.
    assert (101, 302) in assignment_pairs

    # Noa should fill the remaining shift.
    assert assignment_pairs == {
        (101, 302),
        (102, 301)
    }

    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

def test_optimizer_distributes_shifts_fairly():
    employees = [
        Employee(101, "Dana", 4, 4),
        Employee(102, "Noa", 4, 4),
        Employee(103, "Roni", 4, 4),
    ]

    shifts = [
        Shift(
            shift_id=401 + i,
            shift_date=date(2026, 11, 8 + i),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
        for i in range(4)
    ]

    availabilities = [
        Availability(
            employee.employee_id,
            shift.shift_id,
            AvailabilityStatus.AVAILABLE
        )
        for employee in employees
        for shift in shifts
    ]

    assignments = optimize_schedule(
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

    # Coverage must remain optimal.
    assert len(assignments) == 4

    # Employees with identical constraints should
    # receive nearly equal numbers of shifts.
    assert max(counts.values()) - min(counts.values()) <= 1

    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

def test_optimizer_rejects_conflicting_existing_assignments():
    import pytest
    from assignment import Assignment

    employees = [
        Employee(101, "Dana", 1, 1)
    ]

    shifts = [
        Shift(
            shift_id=501,
            shift_date=date(2026, 11, 8),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        ),
        Shift(
            shift_id=502,
            shift_date=date(2026, 11, 9),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
    ]

    availabilities = [
        Availability(101, 501, AvailabilityStatus.AVAILABLE),
        Availability(101, 502, AvailabilityStatus.AVAILABLE)
    ]

    existing_assignments = [
        Assignment(101, 501),
        Assignment(101, 502)
    ]

    with pytest.raises(
        ValueError,
        match="No feasible schedule"
    ):
        optimize_schedule(
            employees,
            shifts,
            availabilities,
            existing_assignments=existing_assignments
        )

def test_optimizer_respects_preferred_shift_counts():
    employees = [
        Employee(101, "Dana", 4, 1),
        Employee(102, "Noa", 4, 3),
    ]

    shifts = [
        Shift(
            shift_id=601 + i,
            shift_date=date(2026, 11, 8 + i),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
        for i in range(4)
    ]

    availabilities = [
        Availability(
            employee.employee_id,
            shift.shift_id,
            AvailabilityStatus.AVAILABLE
        )
        for employee in employees
        for shift in shifts
    ]

    assignments = optimize_schedule(
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

    # All staffing positions must be filled.
    assert len(assignments) == 4

    # Match employee preferences when possible.
    assert counts[101] == 1
    assert counts[102] == 3

    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

def test_optimizer_returns_consistent_assignments():
    employees = [
        Employee(101, "Dana", 2, 2),
        Employee(102, "Noa", 2, 2),
        Employee(103, "Roni", 2, 2),
    ]

    shifts = [
        Shift(
            shift_id=701 + i,
            shift_date=date(2026, 11, 8 + i),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
        for i in range(3)
    ]

    availabilities = [
        Availability(
            employee.employee_id,
            shift.shift_id,
            AvailabilityStatus.AVAILABLE
        )
        for employee in employees
        for shift in shifts
    ]

    first_result = optimize_schedule(
        employees, shifts, availabilities
    )

    second_result = optimize_schedule(
        employees, shifts, availabilities
    )

    first_pairs = {
        (a.employee_id, a.shift_id)
        for a in first_result
    }

    second_pairs = {
        (a.employee_id, a.shift_id)
        for a in second_result
    }

    assert first_pairs == second_pairs




