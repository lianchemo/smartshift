
from sample_data import (
    create_sample_employees,
    create_sample_shifts,
    create_sample_availabilities
)

from scheduler import generate_schedule
from database.assignment_repository import (
    add_assignments,
    get_all_assignments
)


employees = create_sample_employees()
shifts = create_sample_shifts()
availabilities = create_sample_availabilities(
    employees,
    shifts
)

assignments = generate_schedule(
    employees,
    shifts,
    availabilities
)

print("Generated assignments:", len(assignments))

add_assignments(assignments)

saved_assignments = get_all_assignments()

print("Saved assignments:", len(saved_assignments))
