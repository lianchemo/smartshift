
from availability import AvailabilityStatus
from collections import Counter


def find_flexible_employees(shift_id, employees, availabilities):
    flexible_employees = []

    employees_by_id = {
        employee.employee_id: employee
        for employee in employees
    }

    for availability in availabilities:

        if availability.shift_id != shift_id:
            continue

        if availability.status != AvailabilityStatus.FLEXIBLE:
            continue

        employee = employees_by_id.get(
            availability.employee_id
        )

        if employee is not None:
            flexible_employees.append(employee)

    return flexible_employees

def filter_eligible_employees(
    shift,
    flexible_employees,
    shifts,
    assignments
):
    eligible_employees = []

    shift_counts = Counter(
        assignment.employee_id
        for assignment in assignments
    )

    shifts_by_id = {
        s.shift_id: s
        for s in shifts
    }

    for employee in flexible_employees:

        # Check maximum shifts
        if shift_counts[employee.employee_id] >= employee.max_shifts:
            continue

        # Check existing assignments and overlaps
        has_conflict = False

        for assignment in assignments:
            if assignment.employee_id != employee.employee_id:
                continue

            assigned_shift = shifts_by_id[assignment.shift_id]

            if assigned_shift.shift_id == shift.shift_id:
                has_conflict = True
                break

            if (
                assigned_shift.date == shift.date
                and assigned_shift.start_time < shift.end_time
                and shift.start_time < assigned_shift.end_time
            ):
                has_conflict = True
                break

        if has_conflict:
            continue

        eligible_employees.append(employee)

    return eligible_employees

def rank_eligible_employees(eligible_employees, assignments):
    shift_counts = Counter(
        assignment.employee_id
        for assignment in assignments
    )

    def ranking_key(employee):
        current_shifts = shift_counts[employee.employee_id]

        missing_preferred = max(
            0,
            employee.preferred_shifts - current_shifts
        )

        return (
            -missing_preferred,
            current_shifts,
            employee.employee_id
        )

    return sorted(eligible_employees, key=ranking_key)

