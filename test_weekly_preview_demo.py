
from datetime import date

from database.assignment_repository import get_all_assignments
from database.weekly_schedule_service import (
    generate_weekly_schedule_preview
)


def run_demo():
    # Select one specific week.
    week_start = date(2026, 11, 15)

    saved_assignments = get_all_assignments()

    preview_assignments = generate_weekly_schedule_preview(
        week_start=week_start
    )

    print("Saved assignments (all weeks):", len(saved_assignments))
    print("Preview assignments (selected week):", len(preview_assignments))


if __name__ == "__main__":
    run_demo()
