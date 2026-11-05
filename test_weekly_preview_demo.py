
from database.assignment_repository import get_all_assignments
from database.weekly_schedule_service import (
    generate_weekly_schedule_preview
)


saved_assignments = get_all_assignments()

preview_assignments = generate_weekly_schedule_preview()

print("Saved assignments:", len(saved_assignments))
print("Preview assignments:", len(preview_assignments))
print(
    "New proposed assignments:",
    len(preview_assignments) - len(saved_assignments)
)
