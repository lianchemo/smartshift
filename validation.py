
from collections import Counter
from availability import AvailabilityStatus


def validate_schedule(employees, shifts, availabilities, assignments):
    errors = []

    employees_by_id = {e.employee_id: e for e in employees}
    shifts_by_id = {s.shift_id: s for s in shifts}

    availability_lookup = {
        (a.employee_id, a.shift_id): a.status
        for a in availabilities
    }

    employee_counts = Counter()
    shift_counts = Counter()
    employee_assignments = {}

    for assignment in assignments:
        employee_id = assignment.employee_id
        shift_id = assignment.shift_id

        if employee_id not in employees_by_id:
            errors.append(f"Unknown employee: {employee_id}")
            continue

        if shift_id not in shifts_by_id:
            errors.append(f"Unknown shift: {shift_id}")
            continue

        employee_counts[employee_id] += 1
        shift_counts[shift_id] += 1

        status = availability_lookup.get((employee_id, shift_id))

        if status != AvailabilityStatus.AVAILABLE:
            errors.append(
                f"Employee {employee_id} is not available for shift {shift_id}"
            )

        employee_assignments.setdefault(employee_id, []).append(
            shifts_by_id[shift_id]
        )

    for employee_id, count in employee_counts.items():
        employee = employees_by_id[employee_id]

        if count > employee.max_shifts:
            errors.append(
                f"Employee {employee_id} exceeded max shifts"
            )

    for shift_id, count in shift_counts.items():
        shift = shifts_by_id[shift_id]

        if count > shift.required_employees:
            errors.append(
                f"Shift {shift_id} has too many employees"
            )

    for employee_id, assigned_shifts in employee_assignments.items():
        for i in range(len(assigned_shifts)):
            for j in range(i + 1, len(assigned_shifts)):
                first = assigned_shifts[i]
                second = assigned_shifts[j]

                if (
                    first.date == second.date
                    and first.start_time < second.end_time
                    and second.start_time < first.end_time
                ):
                    errors.append(
                        f"Employee {employee_id} has overlapping shifts"
                    )

    return errors
