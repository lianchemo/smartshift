
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

def main():
    print("Welcome to SmartShift!")

    employee1 = Employee(101, "Dana", 4, 3)
    employee2 = Employee(102, "Noa", 5, 4)

    print("\n--- Employees ---")
    print(employee1)
    print(employee2)

    shift1 = Shift(
        201,
        date(2026, 11, 5),
        time(16, 0),
        time(23, 0),
        4
    )
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

    print("\n--- Shifts ---")
    print(shift1)
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
    print("\n--- Assignments ---")

    assignment1 = Assignment(101, 201)

    print(assignment1)
    print("\n--- Sample Employees ---")

    employees = create_sample_employees()

    for employee in employees:
        print(employee)

    print("\n--- Sample Shifts ---")

    shifts = create_sample_shifts()

    for shift in shifts:
        print(shift)

    print(f"\nTotal shifts: {len(shifts)}")
    print("\n--- Sample Availabilities ---")

    availabilities = create_sample_availabilities(employees, shifts)

    for availability in availabilities[:10]:
        print(availability)

    print(f"\nTotal availabilities: {len(availabilities)}")
    print("\n--- Generated Schedule ---")

    assignments = generate_schedule(
        employees,
        shifts,
        availabilities
    )

    for assignment in assignments:
        print(assignment)

    print(f"\nTotal assignments: {len(assignments)}")
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
    print(f"Total missing employees: {sum(gap['missing'] for gap in gaps)}")


if __name__ == "__main__":
    main()
