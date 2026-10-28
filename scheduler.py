
from assignment import Assignment
from availability import AvailabilityStatus


def generate_schedule(employees, shifts, availabilities):
    assignments = []

    shift_counts = {
        employee.employee_id: 0
        for employee in employees
    }

    availability_lookup = {
        (a.employee_id, a.shift_id): a.status
        for a in availabilities
    }

    for shift in shifts:
        assigned_count = 0

        for employee in employees:
            if assigned_count >= shift.required_employees:
                break

            status = availability_lookup.get(
                (employee.employee_id, shift.shift_id)
            )

            if status != AvailabilityStatus.AVAILABLE:
                continue

            if shift_counts[employee.employee_id] >= employee.max_shifts:
                continue

            has_overlap = False

            for assignment in assignments:
                if assignment.employee_id != employee.employee_id:
                    continue

                assigned_shift = next(
                    s for s in shifts
                    if s.shift_id == assignment.shift_id
                )

                if (
                    shift.date == assigned_shift.date
                    and shift.start_time < assigned_shift.end_time
                    and assigned_shift.start_time < shift.end_time
                ):
                    has_overlap = True
                    break

            if has_overlap:
                continue

            assignments.append(
                Assignment(employee.employee_id, shift.shift_id)
            )

            shift_counts[employee.employee_id] += 1
            assigned_count += 1

    return assignments
