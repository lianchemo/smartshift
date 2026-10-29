
from availability_repository import (
    update_availability,
    get_all_availabilities
)


update_availability(107, 213, "available")

records = get_all_availabilities()

for record in records:
    if record.employee_id == 107 and record.shift_id == 213:
        print("Saved status:", record.status)
