
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus

from scheduler import generate_schedule
from validation import validate_schedule
from staffing import find_staffing_gaps

from recommendations import (
    find_flexible_employees,
    filter_eligible_employees,
    rank_eligible_employees
)

from staffing_request import (
    StaffingRequest,
    apply_approved_request
)


def create_staffing_request_test_data():
    """
    Create a predictable staffing shortage:
    Dana is available for shift 212.
    Roni is flexible for shift 213.
    """
    employees = [
        Employee(
            employee_id=101,
            name="Dana",
            max_shifts=1,
            preferred_shifts=1
        ),
        Employee(
            employee_id=107,
            name="Roni",
            max_shifts=1,
            preferred_shifts=1
        )
    ]

    shifts = [
        Shift(
            shift_id=212,
            shift_date=date(2026, 11, 6),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        ),
        Shift(
            shift_id=213,
            shift_date=date(2026, 11, 7),
            start_time=time(8, 0),
            end_time=time(16, 0),
            required_employees=1
        )
    ]

    availabilities = [
        Availability(
            employee_id=101,
            shift_id=212,
            status=AvailabilityStatus.AVAILABLE
        ),
        Availability(
            employee_id=107,
            shift_id=213,
            status=AvailabilityStatus.FLEXIBLE
        )
    ]

    return employees, shifts, availabilities


def test_staffing_shortage_resolved_after_approval():
    # Arrange
    employees, shifts, availabilities = (
        create_staffing_request_test_data()
    )

    # Step 1 - Generate initial schedule
    assignments = generate_schedule(
        employees, shifts, availabilities
    )

    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

    initial_pairs = {
        (a.employee_id, a.shift_id)
        for a in assignments
    }

    assert initial_pairs == {(101, 212)}

    # Step 2 - Identify staffing shortage
    gaps = find_staffing_gaps(shifts, assignments)

    assert len(gaps) == 1
    assert gaps[0]["shift_id"] == 213
    assert gaps[0]["missing"] == 1

    # Step 3 - Find and rank eligible employees
    shift = next(
        s for s in shifts
        if s.shift_id == 213
    )

    flexible = find_flexible_employees(
        213, employees, availabilities
    )

    eligible = filter_eligible_employees(
        shift, flexible, shifts, assignments
    )

    ranked = rank_eligible_employees(
        eligible, assignments
    )

    assert len(ranked) == 1
    assert ranked[0].employee_id == 107

    # Step 4 - Simulate Roni's approval
    request = StaffingRequest(1, 107, 213)
    request.accept()

    apply_approved_request(request, availabilities)

    # Step 5 - Generate updated schedule
    updated_assignments = generate_schedule(
        employees,
        shifts,
        availabilities,
        existing_assignments=assignments
    )

    assert validate_schedule(
        employees, shifts, availabilities, updated_assignments
    ) == []

    updated_pairs = {
        (a.employee_id, a.shift_id)
        for a in updated_assignments
    }

    assert updated_pairs == {
        (101, 212),
        (107, 213)
    }

    assert find_staffing_gaps(
        shifts, updated_assignments
    ) == []


def test_approved_request_preserves_existing_assignments():
    # Arrange
    employees, shifts, availabilities = (
        create_staffing_request_test_data()
    )

    original_assignments = generate_schedule(
        employees, shifts, availabilities
    )

    original_pairs = {
        (a.employee_id, a.shift_id)
        for a in original_assignments
    }

    assert original_pairs == {(101, 212)}

    # Approve Roni for shift 213
    request = StaffingRequest(1, 107, 213)
    request.accept()

    apply_approved_request(request, availabilities)

    # Act - Complete schedule while preserving assignments
    updated_assignments = generate_schedule(
        employees,
        shifts,
        availabilities,
        existing_assignments=original_assignments
    )

    updated_pairs = {
        (a.employee_id, a.shift_id)
        for a in updated_assignments
    }

    # Assert - Existing assignments remain unchanged
    assert original_pairs.issubset(updated_pairs)

    # Only Roni's new assignment was added
    assert updated_pairs - original_pairs == {(107, 213)}

    assert len(updated_assignments) == 2

    assert validate_schedule(
        employees, shifts, availabilities, updated_assignments
    ) == []

    assert find_staffing_gaps(
        shifts, updated_assignments
    ) == []
