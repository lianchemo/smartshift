
from ortools.sat.python import cp_model

from assignment import Assignment
from availability import AvailabilityStatus


def optimize_schedule(
    employees,
    shifts,
    availabilities,
    existing_assignments=None
):
    model = cp_model.CpModel()

    availability_lookup = {
        (a.employee_id, a.shift_id): a.status
        for a in availabilities
    }

    # Create a decision variable for every eligible pair.
    x = {}

    for employee in employees:
        for shift in shifts:
            if availability_lookup.get(
                (employee.employee_id, shift.shift_id)
            ) == AvailabilityStatus.AVAILABLE:
                x[(employee.employee_id, shift.shift_id)] = (
                    model.new_bool_var(
                        f"employee_{employee.employee_id}_shift_{shift.shift_id}"
                    )
                )

    # Preserve existing assignments as mandatory constraints.
    existing_assignments = list(existing_assignments or [])

    for assignment in existing_assignments:
        key = (
            assignment.employee_id,
            assignment.shift_id
        )

        if key not in x:
            raise ValueError(
                f"Existing assignment {key} is not eligible "
                "for this schedule."
            )

        model.add(x[key] == 1)

    # Do not exceed the staffing requirement of each shift.
    for shift in shifts:
        model.add(
            sum(
                x[(employee.employee_id, shift.shift_id)]
                for employee in employees
                if (employee.employee_id, shift.shift_id) in x
            ) <= shift.required_employees
        )

    # Respect each employee's maximum number of shifts.
    for employee in employees:
        model.add(
            sum(
                x[(employee.employee_id, shift.shift_id)]
                for shift in shifts
                if (employee.employee_id, shift.shift_id) in x
            ) <= employee.max_shifts
        )

    # Prevent overlapping shifts for the same employee.
    for employee in employees:
        for i, first_shift in enumerate(shifts):
            for second_shift in shifts[i + 1:]:
                overlaps = (
                    first_shift.date == second_shift.date
                    and first_shift.start_time < second_shift.end_time
                    and second_shift.start_time < first_shift.end_time
                )

                if overlaps:
                    first_key = (
                        employee.employee_id,
                        first_shift.shift_id
                    )
                    second_key = (
                        employee.employee_id,
                        second_shift.shift_id
                    )

                    if first_key in x and second_key in x:
                        model.add(x[first_key] + x[second_key] <= 1)


    # Count assignments for each employee.
    employee_loads = {}

    for employee in employees:
        employee_loads[employee.employee_id] = sum(
            x[(employee.employee_id, shift.shift_id)]
            for shift in shifts
            if (employee.employee_id, shift.shift_id) in x
        )

    # Measure the difference between the busiest
    # and least busy employee.
    max_load = model.new_int_var(
        0, len(shifts), "max_load"
    )
    min_load = model.new_int_var(
        0, len(shifts), "min_load"
    )

    for employee in employees:
        model.add(
            employee_loads[employee.employee_id] <= max_load
        )
        model.add(
            employee_loads[employee.employee_id] >= min_load
        )


    # Step 1: Maximize staffing coverage.
    coverage = sum(x.values())

    model.maximize(coverage)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status != cp_model.OPTIMAL:
        raise ValueError(
            "No feasible schedule or optimization incomplete."
        )

    best_coverage = int(solver.value(coverage))

    # Never sacrifice coverage for preferences or fairness.
    model.add(coverage == best_coverage)

    # Step 2: Measure deviation from employee preferences.
    preference_deviations = []

    for employee in employees:
        employee_id = employee.employee_id
        preferred = employee.preferred_shifts

        deviation = model.new_int_var(
            0,
            max(len(shifts), preferred),
            f"preference_deviation_{employee_id}"
        )

        model.add_abs_equality(
            deviation,
            employee_loads[employee_id] - preferred
        )

        preference_deviations.append(deviation)

    # Preferences come before equal distribution.
    # Fairness is used to break ties.
    fairness_gap = max_load - min_load
    preference_weight = len(shifts) + 1

    model.minimize(
        preference_weight * sum(preference_deviations)
        + fairness_gap
    )

    status = solver.solve(model)

    if status != cp_model.OPTIMAL:
        raise ValueError(
            "No feasible schedule or optimization incomplete."
        )


    return [
        Assignment(employee_id, shift_id)
        for (employee_id, shift_id), variable in x.items()
        if solver.value(variable) == 1
    ]
