
from datetime import date, time

from employee import Employee
from shift import Shift
from availability import Availability, AvailabilityStatus
from assignment import Assignment


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


if __name__ == "__main__":
    main()
