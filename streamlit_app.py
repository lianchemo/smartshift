
import streamlit as st
from database.weekly_schedule_status_repository import (
    get_weekly_schedule_status,
    publish_weekly_schedule
)
from datetime import time, datetime
from zoneinfo import ZoneInfo

from database.weekly_deadline_repository import (
    save_weekly_deadline,
    get_weekly_deadline
)
from database.weekly_shift_service import create_weekly_shifts
from datetime import date, timedelta
from database.weekly_schedule_service import (
    generate_weekly_schedule_preview,
    approve_weekly_schedule,
    get_weekly_schedule_fingerprint
)
from database.request_service import (
    accept_and_assign_request,
    decline_staffing_request
)
from database.employee_repository import get_all_employees
from database.shift_repository import get_all_shifts
from database.availability_repository import (
    get_all_availabilities,
    save_weekly_availability
)
from database.assignment_repository import get_all_assignments

from database.staffing_request_repository import (
    add_staffing_request,
    get_all_staffing_requests
)

from database.converters import (
    employee_from_db,
    shift_from_db,
    availability_from_db,
    assignment_from_db
)

from staffing import find_staffing_gaps

from recommendations import (
    find_flexible_employees,
    filter_eligible_employees,
    rank_eligible_employees
)


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="SmartShift",
    page_icon="📅",
    layout="wide"
)


# --------------------------------------------------
# Load data from SQLite
# --------------------------------------------------

employees = [
    employee_from_db(row)
    for row in get_all_employees()
]

shifts = [
    shift_from_db(row)
    for row in get_all_shifts()
]

availabilities = [
    availability_from_db(row)
    for row in get_all_availabilities()
]

assignments = [
    assignment_from_db(row)
    for row in get_all_assignments()
]

staffing_requests = get_all_staffing_requests()


# --------------------------------------------------
# Calculate staffing gaps
# --------------------------------------------------

gaps = find_staffing_gaps(
    shifts,
    assignments
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

employee_names = {
    employee.employee_id: employee.name
    for employee in employees
}


# --------------------------------------------------
# Navigation
# --------------------------------------------------

st.title("📅 SmartShift")

view = st.sidebar.radio(
    "Navigation",
    ["Manager Dashboard", "Employee Portal"]
)

st.sidebar.caption(
    "SQLite-backed demo"
)


# --------------------------------------------------
# Manager Dashboard
# --------------------------------------------------

if view == "Manager Dashboard":

    st.subheader("Manager Dashboard")

    st.write(
        "Overview of your weekly employee schedule"
    )

    # ----------------------------------------------
    # Weekly availability deadline
    # ----------------------------------------------

    st.divider()
    st.subheader("⏰ Weekly Availability Deadline")

    st.write(
        "Set the last date and time employees "
        "can submit their weekly availability."
    )

    deadline_week_date = st.date_input(
        "Select the scheduling week",
        value=date(2026, 11, 15),
        key="deadline_week_date"
    )

    deadline_week_start = (
        deadline_week_date
        - timedelta(
            days=(deadline_week_date.weekday() + 1) % 7
        )
    )

    st.caption(
        f"Week: {deadline_week_start:%d/%m/%Y} - "
        f"{deadline_week_start + timedelta(days=6):%d/%m/%Y}"
    )

    existing_deadline = get_weekly_deadline(
        deadline_week_start
    )

    default_deadline_date = (
        existing_deadline.date()
        if existing_deadline is not None
        else deadline_week_start - timedelta(days=3)
    )

    default_deadline_time = (
        existing_deadline.time()
        if existing_deadline is not None
        else time(20, 0)
    )

    with st.form(
        key=f"weekly_deadline_form_{deadline_week_start}"
    ):

        deadline_date = st.date_input(
            "Submission deadline date",
            value=default_deadline_date,
            key=f"deadline_date_{deadline_week_start}"
        )

        deadline_time = st.time_input(
            "Submission deadline time (Israel time)",
            value=default_deadline_time,
            key=f"deadline_time_{deadline_week_start}"
        )

        save_deadline_clicked = st.form_submit_button(
            "💾 Save Deadline"
        )

    if save_deadline_clicked:

        try:
            save_weekly_deadline(
                week_start=deadline_week_start,
                deadline_date=deadline_date,
                deadline_time=deadline_time
            )

        except ValueError as error:
            st.error(str(error))

        else:
            st.session_state["deadline_saved_message"] = (
                "Weekly availability deadline saved!"
            )
            st.rerun()

    if "deadline_saved_message" in st.session_state:
        st.success(
            st.session_state.pop("deadline_saved_message")
        )

    if existing_deadline is not None:
        st.info(
            "Current deadline: "
            f"{existing_deadline:%d/%m/%Y %H:%M} "
            "(Israel time)"
        )
    else:
        st.warning(
            "No availability deadline has been set "
            "for this week."
        )



    # ----------------------------------------------
    # Weekly dashboard statistics
    # ----------------------------------------------

    # Use the week selected in Generate Weekly Schedule
    dashboard_date = st.session_state.get(
        "schedule_week_date",
        date(2026, 11, 8)
    )

    dashboard_week_start = dashboard_date - timedelta(
        days=(dashboard_date.weekday() + 1) % 7
    )

    dashboard_week_end = (
        dashboard_week_start + timedelta(days=6)
    )

    # Filter shifts for the selected week
    dashboard_shifts = [
        shift
        for shift in shifts
        if dashboard_week_start <= shift.date <= dashboard_week_end
    ]

    dashboard_shift_ids = {
        shift.shift_id
        for shift in dashboard_shifts
    }

    # Filter saved assignments for those shifts
    dashboard_assignments = [
        assignment
        for assignment in assignments
        if assignment.shift_id in dashboard_shift_ids
    ]

    total_employees = len(employees)
    total_shifts = len(dashboard_shifts)
    assigned_slots = len(dashboard_assignments)

    required_slots = sum(
        shift.required_employees
        for shift in dashboard_shifts
    )

    missing_employees = sum(
        max(
            0,
            shift.required_employees - sum(
                1
                for assignment in dashboard_assignments
                if assignment.shift_id == shift.shift_id
            )
        )
        for shift in dashboard_shifts
    )


    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Employees",
        total_employees
    )

    col2.metric(
        "Total Shifts",
        total_shifts
    )

    col3.metric(
        "Assigned Slots",
        f"{assigned_slots}/{required_slots}"
    )

    col4.metric(
        "Missing Employees",
        missing_employees
    )


    # ----------------------------------------------
    # Create weekly shifts
    # ----------------------------------------------

    st.divider()
    st.subheader("📅 Create Weekly Shifts")

    st.write(
        "Set the number of employees required "
        "for each shift of the selected week."
    )

    new_week_date = st.date_input(
        "Select a date in the new week",
        value=date(2026, 11, 8),
        key="create_week_date"
    )

    days_since_sunday = (
        new_week_date.weekday() + 1
    ) % 7

    new_week_start = (
        new_week_date
        - timedelta(days=days_since_sunday)
    )

    st.caption(
        f"Week: {new_week_start:%d/%m/%Y} - "
        f"{new_week_start + timedelta(days=6):%d/%m/%Y}"
    )

    shift_templates = [
        ("Morning", "08:00–16:00"),
        ("Evening", "16:00–23:00")
    ]

    day_names = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    existing_shift_lookup = {
        (
            shift.date,
            shift.start_time.strftime("%H:%M")
        ): shift
        for shift in shifts
    }

    staffing_requirements = []

    with st.form(
        key=f"create_week_form_{new_week_start}"
    ):

        st.write("### Staffing Requirements")

        for day_offset, day_name in enumerate(day_names):

            current_date = (
                new_week_start
                + timedelta(days=day_offset)
            )

            st.write(
                f"**{day_name} — {current_date:%d/%m/%Y}**"
            )

            col_morning, col_evening = st.columns(2)

            for shift_index, (
                shift_name,
                shift_hours
            ) in enumerate(shift_templates):

                shift_start_hour = (
                    "08:00"
                    if shift_index == 0
                    else "16:00"
                )

                existing_shift = existing_shift_lookup.get(
                    (current_date, shift_start_hour)
                )

                default_count = (
                    4 if day_offset >= 5 else 2
                )

                if existing_shift is not None:
                    default_count = (
                        existing_shift.required_employees
                    )

                current_column = (
                    col_morning
                    if shift_index == 0
                    else col_evening
                )

                with current_column:

                    count = st.number_input(
                        f"{shift_name} ({shift_hours})",
                        min_value=1,
                        max_value=20,
                        value=int(default_count),
                        step=1,
                        disabled=existing_shift is not None,
                        key=(
                            f"staff_count_{current_date}_"
                            f"{shift_index}"
                        )
                    )

                    if existing_shift is not None:
                        st.caption(
                            "Existing shift — staffing "
                            "requirement is locked."
                        )

                staffing_requirements.append(int(count))

            st.divider()

        submitted_week = st.form_submit_button(
            "📅 Create Weekly Shifts"
        )

    if submitted_week:

        try:
            created_count = create_weekly_shifts(
                week_start=new_week_start,
                staffing_requirements=staffing_requirements
            )

        except ValueError as error:
            st.error(str(error))

        else:
            st.session_state["week_creation_message"] = (
                f"{created_count} new shifts created!"
            )
            st.rerun()

    if "week_creation_message" in st.session_state:
        st.success(
            st.session_state.pop("week_creation_message")
        )

    # ----------------------------------------------
    # Weekly availability tracking
    # ----------------------------------------------

    st.divider()
    st.subheader("📋 Weekly Availability Tracking")

    st.write(
        "Track which employees have submitted their "
        "availability for the selected week."
    )

    tracking_date = st.date_input(
        "Select a week to track",
        value=date(2026, 11, 8),
        key="tracking_week_date"
    )

    tracking_week_start = tracking_date - timedelta(
        days=(tracking_date.weekday() + 1) % 7
    )

    tracking_week_end = (
        tracking_week_start + timedelta(days=6)
    )

    st.caption(
        f"Week: {tracking_week_start:%d/%m/%Y} - "
        f"{tracking_week_end:%d/%m/%Y}"
    )

    tracking_shifts = [
        shift
        for shift in shifts
        if tracking_week_start <= shift.date <= tracking_week_end
    ]

    total_tracking_shifts = len(tracking_shifts)

    tracking_shift_ids = {
        shift.shift_id
        for shift in tracking_shifts
    }

    # Look up availability submissions from SQLite.
    submitted_shift_ids = {}

    for availability in availabilities:
        if availability.shift_id not in tracking_shift_ids:
            continue

        submitted_shift_ids.setdefault(
            availability.employee_id,
            set()
        ).add(availability.shift_id)

    # Assigned shifts are locked in the Employee Portal.
    assigned_shift_ids_by_employee = {}

    for assignment in assignments:
        if assignment.shift_id not in tracking_shift_ids:
            continue

        assigned_shift_ids_by_employee.setdefault(
            assignment.employee_id,
            set()
        ).add(assignment.shift_id)

    tracking_rows = []
    completed_employees = 0
    partial_employees = 0
    not_submitted_employees = 0

    if total_tracking_shifts == 0:
        st.info(
            "No shifts have been created for this week."
        )

    else:
        for employee in employees:
            submitted_ids = submitted_shift_ids.get(
                employee.employee_id,
                set()
            )

            assigned_ids = assigned_shift_ids_by_employee.get(
                employee.employee_id,
                set()
            )

            # Already assigned shifts don't require
            # another availability submission.
            covered_ids = submitted_ids | assigned_ids

            completed_count = len(covered_ids)
            missing_count = (
                total_tracking_shifts - completed_count
            )

            if missing_count == 0:
                status = "✅ Complete"
                completed_employees += 1

            elif completed_count == 0:
                status = "⚪ Not submitted"
                not_submitted_employees += 1

            else:
                status = "🟡 Partial"
                partial_employees += 1

            tracking_rows.append({
                "Employee": employee.name,
                "Submitted / Covered": (
                    f"{completed_count}/{total_tracking_shifts}"
                ),
                "Missing": missing_count,
                "Status": status
            })

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Complete",
            completed_employees
        )

        col2.metric(
            "Partial",
            partial_employees
        )

        col3.metric(
            "Not Submitted",
            not_submitted_employees
        )

        st.dataframe(
            tracking_rows,
            use_container_width=True,
            hide_index=True
        )

    # ----------------------------------------------
    # Automatic weekly schedule preview
    # ----------------------------------------------

    st.divider()


    st.subheader("✨ Generate Weekly Schedule")
    if "schedule_approval_message" in st.session_state:
        st.success(
            st.session_state.pop(
                "schedule_approval_message"
            )
        )

    st.write(
        "Select a week to generate an automatic "
        "schedule proposal."
    )

    # Select the first day of the week (Sunday)
    selected_date = st.date_input(
        "Select a date in the week",
        value=date(2026, 11, 1),
        key="schedule_week_date"
    )

    # Calculate the Sunday of the selected week
    days_since_sunday = (selected_date.weekday() + 1) % 7
    week_start = selected_date - timedelta(
        days=days_since_sunday
    )
    week_end = week_start + timedelta(days=6)

    st.info(
        f"Selected week: "
        f"{week_start.strftime('%d/%m/%Y')} - "
        f"{week_end.strftime('%d/%m/%Y')}"
    )

    # Check whether the selected schedule was published
    selected_week_status = get_weekly_schedule_status(
        week_start
    )

    if selected_week_status == "published":
        st.success(
            "✅ This week's schedule is published. "
            "The final schedule is displayed below."
        )

        # Clear any old preview for this week
        if st.session_state.get(
                "preview_week_start"
        ) == week_start:
            st.session_state.pop(
                "schedule_preview", None
            )
            st.session_state.pop(
                "preview_week_start", None
            )

    elif selected_week_status == "approved":
        st.info(
            "✅ This week's schedule is approved "
            "and waiting to be published."
        )

    else:
        if st.button(
                "✨ Generate Schedule Preview",
                key="generate_schedule_preview"
        ):
            st.session_state.schedule_preview = (
                generate_weekly_schedule_preview(
                    week_start=week_start
                )
            )
            st.session_state.preview_week_start = week_start
            st.session_state.preview_fingerprint = (
                get_weekly_schedule_fingerprint(
                    week_start=week_start
                )
            )

    # Show preview only for the selected week
    if (
        "schedule_preview" in st.session_state
        and st.session_state.get(
            "preview_week_start"
        ) == week_start
    ):

        # Show saved assignments together with any new preview
        current_preview = (
            st.session_state.get("schedule_preview", [])
            if st.session_state.get("preview_week_start") == week_start
            else []
        )

        current_week_shift_ids = {
            shift.shift_id
            for shift in shifts
            if week_start <= shift.date <= week_end
        }

        saved_week_assignments = [
            assignment
            for assignment in assignments
            if assignment.shift_id in current_week_shift_ids
        ]

        preview = saved_week_assignments + [
            assignment
            for assignment in current_preview
            if (
                   assignment.employee_id,
                   assignment.shift_id
               ) not in {
                   (saved.employee_id, saved.shift_id)
                   for saved in saved_week_assignments
               }
        ]

        selected_shift_ids = {
            shift.shift_id
            for shift in shifts
            if week_start <= shift.date <= week_end
        }

        saved_pairs = {
            (assignment.employee_id, assignment.shift_id)
            for assignment in assignments
            if assignment.shift_id in selected_shift_ids
        }

        proposed_assignments = [
            assignment
            for assignment in preview
            if (
                assignment.employee_id,
                assignment.shift_id
            ) not in saved_pairs
        ]

        st.success(
            f"Schedule preview generated! "
            f"{len(proposed_assignments)} "
            f"new assignment(s) proposed."
        )

        if not proposed_assignments:
            st.info(
                "No additional assignments available "
                "for this week under the current rules."
            )
        else:
            preview_rows = []

            for assignment in proposed_assignments:
                employee_name = employee_names.get(
                    assignment.employee_id,
                    "Unknown"
                )

                shift = next(
                    (
                        s for s in shifts
                        if s.shift_id == assignment.shift_id
                    ),
                    None
                )

                if shift is None:
                    continue

                preview_rows.append({
                    "Employee": employee_name,
                    "Shift ID": shift.shift_id,
                    "Date": shift.date.strftime("%d/%m/%Y"),
                    "Start": shift.start_time.strftime("%H:%M"),
                    "End": shift.end_time.strftime("%H:%M")
                })

            st.dataframe(
                preview_rows,
                use_container_width=True,
                hide_index=True
            )

    # ------------------------------------------
    # Weekly schedule grid preview
    # ------------------------------------------
    # Get assignments already saved for this week
    current_week_shift_ids = {
        shift.shift_id
        for shift in shifts
        if week_start <= shift.date <= week_end
    }

    saved_week_assignments = [
        assignment
        for assignment in assignments
        if assignment.shift_id in current_week_shift_ids
    ]

    # Include new proposals only for the selected week
    current_preview = (
        st.session_state.get("schedule_preview", [])
        if st.session_state.get("preview_week_start") == week_start
        else []
    )

    saved_pairs = {
        (assignment.employee_id, assignment.shift_id)
        for assignment in saved_week_assignments
    }

    preview = saved_week_assignments + [
        assignment
        for assignment in current_preview
        if (
               assignment.employee_id,
               assignment.shift_id
           ) not in saved_pairs
    ]
    st.subheader("🗓️ Weekly Schedule Grid")

    preview_assignments_by_shift = {}

    for assignment in preview:
        preview_assignments_by_shift.setdefault(
            assignment.shift_id,
            []
        ).append(
            employee_names.get(
                assignment.employee_id,
                "Unknown"
            )
        )

    day_names = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    weekly_grid_rows = []

    for day_offset, day_name in enumerate(day_names):
        current_date = week_start + timedelta(
            days=day_offset
        )

        row = {
            "Day": f"{day_name} {current_date:%d/%m}"
        }

        for label, start_hour in [
            ("Morning 08:00–16:00", "08:00"),
            ("Evening 16:00–23:00", "16:00")
        ]:
            matching_shift = next(
                (
                    shift
                    for shift in shifts
                    if shift.date == current_date
                       and shift.start_time.strftime("%H:%M")
                       == start_hour
                ),
                None
            )

            if matching_shift is None:
                row[label] = "No shift created"
                continue

            names = preview_assignments_by_shift.get(
                matching_shift.shift_id,
                []
            )

            assigned_count = len(names)
            required_count = (
                matching_shift.required_employees
            )

            employee_list = (
                ", ".join(names)
                if names
                else "No employees assigned"
            )

            row[label] = (
                f"{employee_list} "
                f"({assigned_count}/{required_count})"
            )

        weekly_grid_rows.append(row)

    st.dataframe(
        weekly_grid_rows,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "This schedule includes existing saved assignments "
        "and any newly proposed assignments. "
        "Only new assignments require approval."
    )

    # ------------------------------------------
    # Approve and save weekly schedule
    # ------------------------------------------

    st.divider()

    st.subheader("✅ Approve Weekly Schedule")

    st.write(
        "Review the proposed assignments above "
        "before saving them to the database."
    )
    # Get the preview for the currently selected week
    current_preview = (
        st.session_state.get("schedule_preview", [])
        if st.session_state.get("preview_week_start") == week_start
        else []
    )

    # Existing assignments already saved in SQLite
    current_week_shift_ids = {
        shift.shift_id
        for shift in shifts
        if week_start <= shift.date <= week_end
    }

    current_saved_pairs = {
        (assignment.employee_id, assignment.shift_id)
        for assignment in assignments
        if assignment.shift_id in current_week_shift_ids
    }

    proposed_assignments = [
        assignment
        for assignment in current_preview
        if (assignment.employee_id, assignment.shift_id)
           not in current_saved_pairs
    ]

    if proposed_assignments:

        st.info(
            f"{len(proposed_assignments)} new "
            f"assignment(s) are ready for approval."
        )

        if st.button(
                "✅ Approve & Save Schedule",
                key=f"approve_schedule_{week_start}"
        ):
            try:
                saved_count = approve_weekly_schedule(
                    week_start=week_start,
                    expected_new_assignments=proposed_assignments,
                    expected_fingerprint=st.session_state.get(
                        "preview_fingerprint"
                    )
                )

            except ValueError as error:
                st.error(
                    f"Could not approve schedule: {error}"
                )

            else:
                st.session_state["schedule_approval_message"] = (
                    f"{saved_count} assignment(s) "
                    f"saved successfully!"
                )

                # The preview is now outdated.
                st.session_state.pop(
                    "schedule_preview",
                    None
                )
                st.session_state.pop(
                    "preview_week_start",
                    None
                )

                st.rerun()

    else:
        st.info(
            "There are no new assignments to approve."
        )

    # ----------------------------------------------
    # Publish weekly schedule
    # ----------------------------------------------

    st.divider()
    st.subheader("📢 Publish Weekly Schedule")

    publish_week_date = st.date_input(
        "Select a week to publish",
        value=date(2026, 11, 8),
        key="publish_week_date"
    )

    publish_week_start = publish_week_date - timedelta(
        days=(publish_week_date.weekday() + 1) % 7
    )

    st.caption(
        f"Week: {publish_week_start:%d/%m/%Y} - "
        f"{publish_week_start + timedelta(days=6):%d/%m/%Y}"
    )

    schedule_status = get_weekly_schedule_status(
        publish_week_start
    )

    st.write(
        f"**Schedule status:** {schedule_status.upper()}"
    )

    if schedule_status == "published":
        st.success(
            "✅ This weekly schedule has been published."
        )

    elif schedule_status == "approved":
        st.info(
            "This schedule is approved and ready "
            "to be published."
        )

        if st.button(
            "📢 Publish Schedule",
            key=f"publish_schedule_{publish_week_start}"
        ):
            try:
                publish_weekly_schedule(
                    publish_week_start
                )

            except ValueError as error:
                st.error(str(error))

            else:
                st.session_state["publish_message"] = (
                    "Weekly schedule published successfully!"
                )
                st.rerun()

    else:
        st.warning(
            "This schedule must be approved "
            "before it can be published."
        )

    if "publish_message" in st.session_state:
        st.success(
            st.session_state.pop("publish_message")
        )

    # ----------------------------------------------
    # Weekly shift schedule
    # ----------------------------------------------

    st.divider()

    st.subheader("Weekly Shift Schedule")

    schedule_rows = []

    for shift in shifts:
        if not (week_start <= shift.date <= week_end):
            continue

        assigned_count = sum(
            1
            for assignment in assignments
            if assignment.shift_id == shift.shift_id
        )

        missing = (
            shift.required_employees - assigned_count
        )

        schedule_rows.append({
            "Shift ID": shift.shift_id,
            "Date": shift.date.strftime("%d/%m/%Y"),
            "Start": shift.start_time.strftime("%H:%M"),
            "End": shift.end_time.strftime("%H:%M"),
            "Required": shift.required_employees,
            "Assigned": assigned_count,
            "Status": (
                "✅ Covered"
                if missing <= 0
                else "⚠️ Understaffed"
            )
        })

    st.dataframe(
        schedule_rows,
        use_container_width=True,
        hide_index=True
    )

    # ----------------------------------------------
    # Staffing recommendations
    # ----------------------------------------------

    st.divider()

    st.subheader("Staffing Recommendations")

    if not gaps:

        st.success(
            "All shifts are fully staffed!"
        )

    else:

        for gap in gaps:

            shift = next(
                s
                for s in shifts
                if s.shift_id == gap["shift_id"]
            )

            st.warning(
                f"Shift {shift.shift_id} "
                f"({shift.date.strftime('%d/%m/%Y')}, "
                f"{shift.start_time.strftime('%H:%M')}–"
                f"{shift.end_time.strftime('%H:%M')}): "
                f"{gap['missing']} employee(s) missing"
            )

            flexible = find_flexible_employees(
                shift.shift_id,
                employees,
                availabilities
            )

            eligible = filter_eligible_employees(
                shift,
                flexible,
                shifts,
                assignments
            )

            ranked = rank_eligible_employees(
                eligible,
                assignments
            )

            if not ranked:

                st.info(
                    "No eligible flexible employees found."
                )

            else:

                recommendation_rows = []

                for employee in ranked:

                    current_shifts = sum(
                        1
                        for assignment in assignments
                        if assignment.employee_id
                        == employee.employee_id
                    )

                    recommendation_rows.append({
                        "Employee": employee.name,
                        "Current Shifts": current_shifts,
                        "Preferred Shifts": (
                            employee.preferred_shifts
                        ),
                        "Maximum Shifts": (
                            employee.max_shifts
                        )
                    })

                st.dataframe(
                    recommendation_rows,
                    use_container_width=True,
                    hide_index=True
                )

                # Employee selection
                employee_options = {
                    employee.name: employee.employee_id
                    for employee in ranked
                }

                selected_employee_name = st.selectbox(
                    "Select an employee to contact",
                    options=list(employee_options.keys()),
                    key=(
                        f"employee_select_"
                        f"{shift.shift_id}"
                    )
                )

                selected_employee_id = employee_options[
                    selected_employee_name
                ]

                # Check existing pending requests in SQLite
                has_pending_request = any(
                    request.employee_id
                    == selected_employee_id
                    and request.shift_id
                    == shift.shift_id
                    and request.status
                    == "pending"
                    for request in staffing_requests
                )

                if has_pending_request:

                    st.info(
                        "A pending request already exists "
                        "for this employee and shift."
                    )

                # ----------------------------------
                # Send request to SQLite
                # ----------------------------------

                if st.button(
                    "Send Request",
                    key=f"send_request_{shift.shift_id}",
                    disabled=has_pending_request
                ):

                    try:

                        request_id = add_staffing_request(
                            selected_employee_id,
                            shift.shift_id
                        )

                    except ValueError as error:

                        st.error(str(error))

                    else:

                        st.success(
                            f"Request #{request_id} "
                            f"created for "
                            f"{selected_employee_name}!"
                        )

                        st.rerun()

    # ----------------------------------------------
    # Staffing requests from SQLite
    # ----------------------------------------------

    st.divider()

    st.subheader("Staffing Requests")

    if not staffing_requests:

        st.info(
            "No staffing requests yet."
        )

    else:

        request_rows = []

        for request in staffing_requests:

            request_rows.append({
                "Request ID": request.request_id,
                "Employee": employee_names.get(
                    request.employee_id,
                    "Unknown"
                ),
                "Shift ID": request.shift_id,
                "Status": request.status
            })

        st.dataframe(
            request_rows,
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# Employee Portal
# --------------------------------------------------

else:

    st.subheader("Employee Portal")

    st.write(
        "View your shifts and staffing requests."
    )

    st.caption(
        "Demo employee selection — "
        "not a secure login system."
    )

    # ----------------------------------------------
    # Employee selection
    # ----------------------------------------------

    employee_options = {
        employee.name: employee.employee_id
        for employee in employees
    }

    selected_name = st.selectbox(
        "Select employee",
        options=list(employee_options.keys())
    )

    selected_employee_id = employee_options[
        selected_name
    ]

    st.success(
        f"Welcome, {selected_name}!"
    )

    st.write(
        f"Employee ID: {selected_employee_id}"
    )

    # ----------------------------------------------

    # ----------------------------------------------
    # My Weekly Availability
    # ----------------------------------------------

    st.divider()
    st.subheader("My Weekly Availability")

    selected_availability_date = st.date_input(
        "Select a week for availability",
        value=date(2026, 11, 8),
        key="employee_availability_week"
    )

    days_since_sunday = (
        selected_availability_date.weekday() + 1
    ) % 7

    availability_week_start = (
        selected_availability_date
        - timedelta(days=days_since_sunday)
    )

    availability_week_end = (
        availability_week_start + timedelta(days=6)
    )

    st.info(
        f"Selected week: "
        f"{availability_week_start:%d/%m/%Y} - "
        f"{availability_week_end:%d/%m/%Y}"
    )


    # ----------------------------------------------
    # Weekly availability deadline status
    # ----------------------------------------------

    employee_week_deadline = get_weekly_deadline(
        availability_week_start
    )

    availability_is_closed = False

    if employee_week_deadline is None:
        st.warning(
            "No submission deadline has been set "
            "for this week."
        )

    else:
        israel_timezone = ZoneInfo("Asia/Jerusalem")

        deadline_in_israel = (
            employee_week_deadline.replace(
                tzinfo=israel_timezone
            )
        )

        now_in_israel = datetime.now(israel_timezone)

        availability_is_closed = (
            now_in_israel > deadline_in_israel
        )

        st.write(
            f"**Submission deadline:** "
            f"{employee_week_deadline:%d/%m/%Y %H:%M} "
            "(Israel time)"
        )

        if availability_is_closed:
            st.error(
                "🔒 Availability submission is closed. "
                "The deadline has passed."
            )
        else:
            st.success(
                "✅ Availability submission is open."
            )


    weekly_shifts = sorted(
        [
            shift
            for shift in shifts
            if availability_week_start
            <= shift.date
            <= availability_week_end
        ],
        key=lambda shift: (
            shift.date,
            shift.start_time
        )
    )

    employee_availability_lookup = {
        availability.shift_id: availability.status.value
        for availability in availabilities
        if availability.employee_id == selected_employee_id
    }

    assigned_shift_ids = {
        assignment.shift_id
        for assignment in assignments
        if assignment.employee_id == selected_employee_id
    }

    # ----------------------------------------------
    # Weekly availability progress
    # ----------------------------------------------

    total_weekly_shifts = len(weekly_shifts)

    completed_shifts = sum(
        1
        for shift in weekly_shifts
        if shift.shift_id in employee_availability_lookup
    )

    if total_weekly_shifts > 0:
        completion_ratio = (
            completed_shifts / total_weekly_shifts
        )

        st.write(
            f"**Availability submitted: "
            f"{completed_shifts}/{total_weekly_shifts} shifts**"
        )

        st.progress(completion_ratio)

        if completed_shifts == total_weekly_shifts:
            st.success(
                "✅ Your weekly availability is complete!"
            )
        else:
            st.info(
                f"{total_weekly_shifts - completed_shifts} "
                f"shift(s) still need availability."
            )

    if not weekly_shifts:
        st.info(
            "No shifts have been created for this week."
        )

    else:
        st.write(
            "Choose your availability for each shift "
            "and save your preferences."
        )

        status_options = [
            "available",
            "flexible",
            "unavailable"
        ]

        with st.form(
            key=(
                f"availability_form_"
                f"{selected_employee_id}_"
                f"{availability_week_start}"
            )
        ):
            selected_statuses = {}

            for shift in weekly_shifts:
                current_status = (
                    employee_availability_lookup.get(
                        shift.shift_id
                    )
                )

                is_assigned = (
                    shift.shift_id in assigned_shift_ids
                )

                st.write(
                    f"**Shift {shift.shift_id}** — "
                    f"{shift.date:%d/%m/%Y} | "
                    f"{shift.start_time:%H:%M}–"
                    f"{shift.end_time:%H:%M}"
                )

                if is_assigned:
                    st.caption(
                        "Already assigned — "
                        "availability is locked."
                    )

                # Leave shifts without existing availability
                # unselected until the employee chooses.
                options = ["Not submitted"] + status_options

                if current_status in status_options:
                    default_index = options.index(
                        current_status
                    )
                else:
                    default_index = 0

                selected_statuses[shift.shift_id] = (
                    st.selectbox(
                        "Availability",
                        options=options,
                        index=default_index,
                        disabled=is_assigned or availability_is_closed,
                        key=(
                            f"availability_"
                            f"{selected_employee_id}_"
                            f"{shift.shift_id}"
                        )
                    )
                )

                st.divider()

            submitted = st.form_submit_button(
                "💾 Save My Availability",
                disabled=availability_is_closed
            )


        if submitted:
            shift_statuses = {}

            for shift in weekly_shifts:
                if shift.shift_id in assigned_shift_ids:
                    continue

                selected_status = selected_statuses[
                    shift.shift_id
                ]

                if selected_status == "Not submitted":
                    continue

                shift_statuses[shift.shift_id] = selected_status

            if not shift_statuses:
                st.info(
                    "No availability choices were submitted."
                )

            else:
                try:
                    saved_count = save_weekly_availability(
                        employee_id=selected_employee_id,
                        shift_statuses=shift_statuses
                    )

                except ValueError as error:
                    st.error(
                        f"Could not save weekly availability: {error}"
                    )

                else:
                    st.session_state["availability_save_message"] = (
                        f"Availability saved for "
                        f"{saved_count} shift(s)!"
                    )
                    st.rerun()

        if "availability_save_message" in st.session_state:
            st.success(
                st.session_state.pop("availability_save_message")
            )

    # ----------------------------------------------
    # My assigned shifts
    # ----------------------------------------------

    st.divider()

    st.subheader("My Assigned Shifts")

    # Show only assignments from the selected week
    weekly_shift_ids = {
        shift.shift_id
        for shift in weekly_shifts
    }

    # Employees can view only published schedules.
    employee_schedule_status = get_weekly_schedule_status(
        availability_week_start
    )

    if employee_schedule_status == "published":
        my_assignments = [
            assignment
            for assignment in assignments
            if assignment.employee_id == selected_employee_id
               and assignment.shift_id in weekly_shift_ids
        ]
    else:
        my_assignments = []

    if employee_schedule_status != "published":
        st.info(
            "🔒 The schedule for this week "
            "has not been published yet."
        )

    elif not my_assignments:
        st.info(
            "The schedule is published, but you "
            "have no assigned shifts this week."
        )

    else:

        my_shift_rows = []

        for assignment in my_assignments:

            shift = next(
                (
                    s
                    for s in shifts
                    if s.shift_id
                    == assignment.shift_id
                ),
                None
            )

            if shift is None:
                continue

            my_shift_rows.append({
                "Shift ID": shift.shift_id,
                "Date": shift.date.strftime("%d/%m/%Y"),
                "Start": shift.start_time.strftime("%H:%M"),
                "End": shift.end_time.strftime("%H:%M")
            })

        st.dataframe(
            my_shift_rows,
            use_container_width=True,
            hide_index=True
        )

    # ----------------------------------------------
    # My staffing requests from SQLite
    # ----------------------------------------------

    st.divider()

    st.subheader("My Staffing Requests")

    my_requests = [
        request
        for request in staffing_requests
        if request.employee_id
        == selected_employee_id
    ]

    if not my_requests:

        st.info(
            "You have no staffing requests."
        )

    else:

        request_rows = []

        for request in my_requests:

            request_rows.append({
                "Request ID": request.request_id,
                "Shift ID": request.shift_id,
                "Status": request.status
            })

        st.dataframe(
            request_rows,
            use_container_width=True,
            hide_index=True
        )

        # ------------------------------------------
        # Respond to requests
        # ------------------------------------------

        pending_requests = [
            request
            for request in my_requests
            if request.status == "pending"
        ]

        if pending_requests:

            st.subheader("Respond to Requests")

            st.info(
                "Accept and Decline will be enabled "
                "after database-safe request handling "
                "is implemented."
            )


            for request in pending_requests:

                st.write(
                    f"Request #{request.request_id} "
                    f"— Shift {request.shift_id}"
                )

                col_accept, col_decline = st.columns(2)

                with col_accept:

                    if st.button(
                        "✅ Accept",
                        key=f"accept_{request.request_id}"
                    ):

                        try:
                            accept_and_assign_request(
                                request.request_id
                            )

                        except ValueError as error:
                            st.error(
                                f"Cannot accept request: {error}"
                            )

                        else:
                            st.success(
                                "Request accepted! "
                                "You have been assigned "
                                "to the shift."
                            )
                            st.rerun()


                with col_decline:

                    if st.button(
                        "❌ Decline",
                        key=f"decline_{request.request_id}"
                    ):

                        try:
                            decline_staffing_request(
                                request.request_id
                            )

                        except ValueError as error:
                            st.error(
                                f"Cannot decline request: {error}"
                            )

                        else:
                            st.success(
                                "Request declined successfully."
                            )
                            st.rerun()

