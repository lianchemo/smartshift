
from employee import Employee
from datetime import date, time, timedelta
from shift import Shift
from availability import Availability, AvailabilityStatus


def create_sample_employees():
    employees = [
        Employee(101, "Dana", 4, 3),
        Employee(102, "Noa", 5, 4),
        Employee(103, "Maya", 4, 3),
        Employee(104, "Lior", 5, 4),
        Employee(105, "Shira", 3, 2),
        Employee(106, "Amit", 4, 3),
        Employee(107, "Roni", 5, 4),
        Employee(108, "Yael", 4, 3),
        Employee(109, "Tamar", 3, 2),
        Employee(110, "Daniel", 5, 4)
    ]

    return employees


def create_sample_shifts():
    shifts = []
    start_date = date(2026, 11, 1)
    shift_id = 201

    for day in range(7):
        current_date = start_date + timedelta(days=day)

        morning_shift = Shift(
            shift_id,
            current_date,
            time(8, 0),
            time(16, 0),
            2
        )
        shifts.append(morning_shift)
        shift_id += 1

        evening_shift = Shift(
            shift_id,
            current_date,
            time(16, 0),
            time(23, 0),
            2
        )
        shifts.append(evening_shift)
        shift_id += 1

    return shifts


def create_sample_availabilities(employees, shifts):
    availabilities = []

    for shift in shifts:
        for employee in employees:

            if (employee.employee_id + shift.shift_id) % 5 == 0:
                status = AvailabilityStatus.FLEXIBLE

            elif (employee.employee_id + shift.shift_id) % 3 == 0:
                status = AvailabilityStatus.AVAILABLE

            else:
                status = AvailabilityStatus.UNAVAILABLE

            availability = Availability(
                employee.employee_id,
                shift.shift_id,
                status
            )

            availabilities.append(availability)

    return availabilities





