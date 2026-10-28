
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus
from assignment import Assignment
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
from staffing_request import StaffingRequest, apply_approved_request


def main():
    print("Welcome to SmartShift!")

    # ----------------------------------
    # 1. Employee Test
    # ----------------------------------

    employee1 = Employee(101, "Dana", 4, 3)
    employee2 = Employee(102, "Noa", 5, 4)

    print("\n--- Employees ---")
    print(employee1)
    print(employee2)

    # ----------------------------------
    # 2. Shift Test
    # ----------------------------------

    shift1 = Shift(
        201,
        date(2026, 11, 5),
        time(16, 0),
        time(23, 0),
        4
    )

    print("\n--- Shifts ---")
    print(shift1)

    # ----------------------------------
    # 3. Shift Validation Test
    # ----------------------------------

    print("\n--- Validation Test ---")

    try:
        invalid_shift = Shift(
            202,
            date(2026, 11, 5),
            time(23, 0),
            time(16, 0),
            4
        )

        print(invalid_shift)

    except ValueError as error:
        print(f"Validation error: {error}")

    # ----------------------------------
    # 4. Availability Test
    # ----------------------------------

    print("\n--- Availability ---")

    availability1 = Availability(
        101,
        201,
        AvailabilityStatus.AVAILABLE
    )

    availability2 = Availability(
        102,
        201,
        AvailabilityStatus.FLEXIBLE
    )

    print(availability1)
    print(availability2)

    # ----------------------------------
    # 5. Assignment Test
    # ----------------------------------

    print("\n--- Assignments ---")

    assignment1 = Assignment(101, 201)
    print(assignment1)

    # ----------------------------------
    # 6. Sample Employees
    # ----------------------------------

    print("\n--- Sample Employees ---")

    employees = create_sample_employees()

    for employee in employees:
        print(employee)

    # ----------------------------------
    # 7. Sample Shifts
    # ----------------------------------

    print("\n--- Sample Shifts ---")

    shifts = create_sample_shifts()

    for shift in shifts:
        print(shift)

    print(f"\nTotal shifts: {len(shifts)}")

    # ----------------------------------
    # 8. Sample Availabilities
    # ----------------------------------

    print("\n--- Sample Availabilities ---")

    availabilities = create_sample_availabilities(
        employees,
        shifts
    )

    for availability in availabilities[:10]:
        print(availability)

    print(f"\nTotal availabilities: {len(availabilities)}")

    # ----------------------------------
    # 9. Generate Schedule
    # ----------------------------------

    print("\n--- Generated Schedule ---")

    assignments = generate_schedule(
        employees,
        shifts,
        availabilities
    )

    for assignment in assignments:
        print(assignment)

    print(f"\nTotal assignments: {len(assignments)}")

    # ----------------------------------
    # 10. Schedule Validation
    # ----------------------------------

    print("\n--- Schedule Validation ---")

    errors = validate_schedule(
        employees,
        shifts,
        availabilities,
        assignments
    )

    if not errors:
        print("Schedule validation passed!")
    else:
        print("Schedule validation failed!")

        for error in errors:
            print(error)

    # ----------------------------------
    # 11. Staffing Gaps
    # ----------------------------------

    print("\n--- Staffing Gaps ---")

    gaps = find_staffing_gaps(shifts, assignments)

    if not gaps:
        print("All shifts are fully staffed!")
    else:
        for gap in gaps:
            print(
                f"Shift {gap['shift_id']} | "
                f"{gap['date']} | "
                f"Missing: {gap['missing']} employee(s) | "
                f"Assigned: {gap['assigned']}/{gap['required']}"
            )

    print(f"\nTotal understaffed shifts: {len(gaps)}")
    print(
        f"Total missing employees: "
        f"{sum(gap['missing'] for gap in gaps)}"
    )

    # ----------------------------------
    # 12. Staffing Recommendations
    # ----------------------------------

    print("\n--- Staffing Recommendations ---")

    for gap in gaps:
        shift_id = gap["shift_id"]

        print(f"\nShift {shift_id}:")

        # Find flexible employees
        flexible_employees = find_flexible_employees(
            shift_id,
            employees,
            availabilities
        )

        print("\nFlexible employees:")

        if not flexible_employees:
            print("No flexible employees found.")
        else:
            for employee in flexible_employees:
                print(employee)

        # Find the understaffed shift
        shift = next(
            s for s in shifts
            if s.shift_id == shift_id
        )

        # Filter employees by constraints
        eligible_employees = filter_eligible_employees(
            shift,
            flexible_employees,
            shifts,
            assignments
        )

        print("\nEligible employees:")

        if not eligible_employees:
            print("No eligible employees found.")
        else:
            for employee in eligible_employees:
                print(employee)

        # Rank eligible employees
        ranked_employees = rank_eligible_employees(
            eligible_employees,
            assignments
        )

        print(f"\n--- Ranked Recommendations for Shift {shift_id} ---")

        for position, employee in enumerate(
            ranked_employees, start=1
        ):
            current_shifts = sum(
                1 for assignment in assignments
                if assignment.employee_id == employee.employee_id
            )

            print(
                f"{position}. {employee.name} | "
                f"Current: {current_shifts} | "
                f"Preferred: {employee.preferred_shifts}"
            )

        # Show current shift load for flexible employees
        print("\nFlexible employees shift counts:")

        for employee in flexible_employees:
            assigned_count = sum(
                1 for assignment in assignments
                if assignment.employee_id == employee.employee_id
            )

            print(
                f"{employee.name}: "
                f"{assigned_count}/{employee.max_shifts} shifts"
            )

    # ----------------------------------
    # 13. Staffing Request Test
    # ----------------------------------

    print("\n--- Staffing Request Test ---")

    request = StaffingRequest(
        request_id=1,
        employee_id=107,
        shift_id=213
    )

    print(request)

    request.accept()

    print(request)

    print("\n--- Applying Approved Request ---")

    apply_approved_request(request, availabilities)

    print("Roni's availability updated to AVAILABLE.")

    updated_assignments = generate_schedule(
        employees,
        shifts,
        availabilities
    )

    updated_errors = validate_schedule(
        employees,
        shifts,
        availabilities,
        updated_assignments
    )

    if updated_errors:
        print("Updated schedule validation failed!")

        for error in updated_errors:
            print(error)

    else:
        print("Updated schedule validation passed!")

        updated_gaps = find_staffing_gaps(
            shifts,
            updated_assignments
        )

        print(f"Total assignments: {len(updated_assignments)}")
        print(
            f"Total missing employees: "
            f"{sum(gap['missing'] for gap in updated_gaps)}"
        )

        roni_assigned = any(
            assignment.employee_id == 107
            and assignment.shift_id == 213
            for assignment in updated_assignments
        )

        print(f"Roni assigned to Shift 213: {roni_assigned}")



if __name__ == "__main__":
    main()
