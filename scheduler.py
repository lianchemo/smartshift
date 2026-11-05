
from assignment import Assignment
from availability import AvailabilityStatus


def generate_schedule(
    employees,
    shifts,
    availabilities,
    existing_assignments=None
):
    # Keep existing assignments without changing them
    assignments = list(existing_assignments or [])

    # Count how many shifts each employee already has
    shift_counts = {
        employee.employee_id: 0
        for employee in employees
    }

    for assignment in assignments:
        shift_counts[assignment.employee_id] += 1

    # Build availability lookup
    availability_lookup = {
        (a.employee_id, a.shift_id): a.status
        for a in availabilities
    }

    # Build shift lookup
    shift_lookup = {
        shift.shift_id: shift
        for shift in shifts
    }


    # ----------------------------------------------
    # Prioritize the hardest shifts to staff
    # ----------------------------------------------

    def staffing_difficulty(shift):
        available_count = sum(
            1
            for employee in employees
            if availability_lookup.get(
                (employee.employee_id, shift.shift_id)
            ) == AvailabilityStatus.AVAILABLE
        )

        already_assigned_count = sum(
            1
            for assignment in assignments
            if assignment.shift_id == shift.shift_id
        )

        missing_count = max(
            0,
            shift.required_employees - already_assigned_count
        )

        # A shift with fewer available employees
        # per missing position is more difficult.
        if missing_count == 0:
            return float("inf")

        return available_count / missing_count

    prioritized_shifts = sorted(
        shifts,
        key=staffing_difficulty
    )

    for shift in prioritized_shifts:

        # Count employees already assigned to this shift
        assigned_count = sum(
            1
            for assignment in assignments
            if assignment.shift_id == shift.shift_id
        )


        # Count how many shifts each employee is available for
        availability_counts = {
            employee.employee_id: sum(
                1
                for s in shifts
                if availability_lookup.get(
                    (employee.employee_id, s.shift_id)
                ) == AvailabilityStatus.AVAILABLE
            )
            for employee in employees
        }

        # Prefer employees with fewer assignments.
        # When tied, prefer employees with fewer options.
        employees_by_fairness = sorted(
            employees,
            key=lambda employee: (
                shift_counts[employee.employee_id],
                availability_counts[employee.employee_id]
            )
        )

        for employee in employees_by_fairness:

            if assigned_count >= shift.required_employees:
                break

            # Don't assign the same employee twice
            already_assigned = any(
                assignment.employee_id == employee.employee_id
                and assignment.shift_id == shift.shift_id
                for assignment in assignments
            )

            if already_assigned:
                continue

            status = availability_lookup.get(
                (employee.employee_id, shift.shift_id)
            )

            if status != AvailabilityStatus.AVAILABLE:
                continue

            if shift_counts[employee.employee_id] >= employee.max_shifts:
                continue

            # Check overlapping shifts
            has_overlap = False

            for assignment in assignments:
                if assignment.employee_id != employee.employee_id:
                    continue

                assigned_shift = shift_lookup[assignment.shift_id]

                if (
                    shift.date == assigned_shift.date
                    and shift.start_time < assigned_shift.end_time
                    and assigned_shift.start_time < shift.end_time
                ):
                    has_overlap = True
                    break

            if has_overlap:
                continue

            # Assign employee to the shift
            assignments.append(
                Assignment(employee.employee_id, shift.shift_id)
            )

            shift_counts[employee.employee_id] += 1
            assigned_count += 1

    return assignments
