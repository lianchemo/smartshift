
from sample_data import (
    create_sample_employees,
    create_sample_shifts,
    create_sample_availabilities
)

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


def test_staffing_shortage_resolved_after_approval():
    # Arrange - Create sample data
    employees = create_sample_employees()
    shifts = create_sample_shifts()
    availabilities = create_sample_availabilities(
        employees, shifts
    )

    # Step 1 - Generate the initial schedule
    assignments = generate_schedule(
        employees, shifts, availabilities
    )

    assert validate_schedule(
        employees, shifts, availabilities, assignments
    ) == []

    # Step 2 - Identify staffing shortages
    gaps = find_staffing_gaps(shifts, assignments)

    assert len(gaps) == 1
    assert gaps[0]["shift_id"] == 213
    assert gaps[0]["missing"] == 1

    # Step 3 - Find and rank eligible employees
    shift = next(s for s in shifts if s.shift_id == 213)

    flexible = find_flexible_employees(
        213, employees, availabilities
    )

    eligible = filter_eligible_employees(
        shift, flexible, shifts, assignments
    )

    ranked = rank_eligible_employees(
        eligible, assignments
    )

    assert len(ranked) > 0
    assert ranked[0].employee_id == 107

    # Step 4 - Simulate employee approval
    request = StaffingRequest(1, 107, 213)
    request.accept()

    apply_approved_request(request, availabilities)

    # Step 5 - Generate an updated schedule
    updated_assignments = generate_schedule(
        employees, shifts, availabilities
    )

    assert validate_schedule(
        employees, shifts, availabilities, updated_assignments
    ) == []

    updated_gaps = find_staffing_gaps(
        shifts, updated_assignments
    )

    assert updated_gaps == []

    assert any(
        a.employee_id == 107 and a.shift_id == 213
        for a in updated_assignments
    )

def test_approved_request_preserves_existing_assignments():
    # Arrange: create the initial schedule
    employees = create_sample_employees()
    shifts = create_sample_shifts()
    availabilities = create_sample_availabilities(
        employees, shifts
    )

    original_assignments = generate_schedule(
        employees, shifts, availabilities
    )

    original_pairs = {
        (a.employee_id, a.shift_id)
        for a in original_assignments
    }

    assert len(original_pairs) == 27

    # Approve Roni for shift 213
    request = StaffingRequest(1, 107, 213)
    request.accept()

    apply_approved_request(request, availabilities)

    # Act: complete the schedule without replacing assignments
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

    # Assert: all previous assignments remain unchanged
    assert original_pairs.issubset(updated_pairs)

    # Only Roni's new assignment was added
    assert updated_pairs - original_pairs == {(107, 213)}

    assert len(updated_assignments) == 28

    assert validate_schedule(
        employees, shifts, availabilities, updated_assignments
    ) == []

    assert find_staffing_gaps(shifts, updated_assignments) == []
