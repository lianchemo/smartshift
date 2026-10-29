from database.assignment_repository import get_all_assignments
from database.converters import assignment_from_db
from database.employee_repository import get_all_employees
from database.shift_repository import get_all_shifts
from database.availability_repository import get_all_availabilities

from database.converters import (
    employee_from_db,
    shift_from_db,
    availability_from_db
)

from scheduler import generate_schedule


# Load employees
employees = [
    employee_from_db(db_employee)
    for db_employee in get_all_employees()
]

# Load shifts
shifts = [
    shift_from_db(db_shift)
    for db_shift in get_all_shifts()
]

# Load availabilities
availabilities = [
    availability_from_db(db_availability)
    for db_availability in get_all_availabilities()
]

print("Employees:", len(employees))
print("Shifts:", len(shifts))
print("Availabilities:", len(availabilities))

# Generate a schedule using database data
assignments = generate_schedule(
    employees,
    shifts,
    availabilities
)

print("Generated assignments:", len(assignments))

# Load saved assignments from SQLite
db_assignments = get_all_assignments()

saved_assignments = [
    assignment_from_db(db_assignment)
    for db_assignment in db_assignments
]

print("Saved assignments:", len(saved_assignments))

print("\nFirst 5 saved assignments:")

for assignment in saved_assignments[:5]:
    print(
        "Employee:",
        assignment.employee_id,
        "Shift:",
        assignment.shift_id
    )

