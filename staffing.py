
from collections import Counter


def find_staffing_gaps(shifts, assignments):
    gaps = []

    assigned_counts = Counter(
        assignment.shift_id
        for assignment in assignments
    )

    for shift in shifts:
        assigned = assigned_counts[shift.shift_id]
        required = shift.required_employees

        missing = max(0, required - assigned)

        if missing > 0:
            gaps.append({
                "shift_id": shift.shift_id,
                "date": shift.date,
                "start_time": shift.start_time,
                "end_time": shift.end_time,
                "required": required,
                "assigned": assigned,
                "missing": missing
            })

    return gaps
