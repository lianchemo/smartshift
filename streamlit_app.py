import streamlit as st
from database.demo_session import create_demo_engine
from database.weekly_schedule_status_repository import (
    get_weekly_schedule_status,
    publish_weekly_schedule
)
from datetime import time, datetime
from html import escape as html_escape
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
# SmartShift visual system (presentation only)
# --------------------------------------------------
st.markdown("""
<style>
:root { --ss-navy:#142D4E; --ss-teal:#138B91; --ss-muted:#64748b; }
.block-container { max-width: 1320px; padding-top: 1.5rem; padding-bottom: 4rem; }
h1, h2, h3 { letter-spacing: -0.025em; }
h1 { font-weight: 800 !important; }
[data-testid="stMetric"] {
  background: #fff;
  padding: 1.1rem 1.25rem;
  border: 1px solid #E2EAF1;
  border-radius: 16px;
  box-shadow: 0 5px 22px rgba(20,45,78,.045);
  min-height: 112px;
}
[data-testid="stMetricLabel"] { color:#53677D; font-weight:600; }
[data-testid="stMetricValue"] { color:#142D4E; font-weight:800; letter-spacing:-.04em; }
[data-testid="stSidebar"] { background: #F5F8FC; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#142D4E; }
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  border-radius: 10px;
  font-weight: 650;
}
div[data-testid="stExpander"] { border:1px solid #E1EAF1; border-radius:14px; background:#fff; }
.ss-hero {
  border-radius: 20px;
  background: linear-gradient(118deg, #142D4E 0%, #1D5070 65%, #138B91 100%);
  color:#fff;
  padding: 1.85rem 2rem;
  margin-bottom:1.15rem;
  box-shadow: 0 10px 28px rgba(20,45,78,.12);
}
.ss-hero .ss-kicker { font-size:.72rem; font-weight:800; letter-spacing:.15em; color:#BAE4E4; text-transform:uppercase; }
.ss-hero h2 { color:#fff !important; font-size:1.9rem; margin:.5rem 0 .4rem; font-weight:800; }
.ss-hero p { color:#E4EDF4; margin:0; font-size:.94rem; line-height:1.6; }
.ss-section { margin-top: 1.65rem; margin-bottom:.85rem; }
.ss-section h3 { color:#142D4E; margin:0 0 .25rem; font-weight:800; }
.ss-section p { color:#64748b; margin:0; font-size:.87rem; }
.ss-shift-card {
  border:1px solid #E2EAF1; border-radius:14px;
  background:#fff; padding:1rem 1.1rem; margin:.3rem 0;
  min-height:135px;
}
.ss-shift-card .ss-shift-date { font-weight:800; font-size:.85rem; color:#142D4E; margin-bottom:.65rem; }
.ss-shift-card .ss-shift-line { display:flex; gap:.5rem; align-items:center; justify-content:space-between; margin:.4rem 0; font-size:.79rem; color:#42566C; }
.ss-shift-card .ss-chip { border-radius:30px; background:#E7F7F1; color:#19755D; font-weight:750; padding:.14rem .48rem; font-size:.7rem; }
.ss-shift-card .ss-chip.missing { background:#FFF2E4; color:#A66118; }
.ss-chip-muted { display:inline-block; font-size:.75rem; padding:.24rem .65rem; border-radius:30px; background:#E6F5F4; color:#116E73; font-weight:750; }
@media (max-width: 640px) {
 .block-container { padding: 1rem .9rem 3rem; }
 .ss-hero { padding:1.4rem 1.1rem; border-radius:14px; }
 .ss-hero h2 { font-size:1.45rem; }
 [data-testid="stMetric"] { padding:.85rem; min-height:95px; }
}

/* SmartShift v2 — cohesive desktop/mobile experience */
.stApp { background: #F8FAFD; }
.block-container { max-width: 1380px; padding-top: 1.15rem; }
[data-testid="stSidebar"] { border-right: 1px solid #E3EAF1; }
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #DFE8F1; border-radius: 18px; box-shadow: 0 7px 23px rgba(20,45,78,.055); }
.ss-hero { border-radius: 23px; padding: 2.1rem 2.3rem; background: linear-gradient(112deg,#102C4E 0%,#205876 66%,#148D92 100%); }
.ss-hero h2 { font-size: 2.1rem; }
.ss-hero .ss-kicker { letter-spacing: .17em; }
.ss-section { margin-top: 1.3rem; }
.ss-panel { background: #FFFFFF; border:1px solid #E1EAF3; border-radius: 20px; padding: 1.2rem 1.35rem; box-shadow: 0 6px 24px rgba(20,45,78,.035); margin: .55rem 0; }
.ss-eyebrow { font-size:.72rem; text-transform:uppercase; font-weight:800; letter-spacing:.13em; color:#17858A; }
.ss-subtle { color:#60758B; font-size:.83rem; }
.ss-day-title { font-weight:800; font-size:.93rem; color:#142D4E; padding-bottom:.6rem; border-bottom:1px solid #EFF3F7; margin-bottom:.75rem; }
.ss-slot { padding:.55rem 0; }
.ss-slot + .ss-slot { border-top:1px solid #F0F3F7; }
.ss-slot-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.3rem; }
.ss-slot-title { color:#1C405D; font-size:.81rem; font-weight:750; }
.ss-slot-names { color:#64748b; font-size:.78rem; margin-top:.3rem; line-height:1.5; overflow-wrap:anywhere; }
.ss-status { display:inline-block; border-radius:999px; padding:.16rem .55rem; font-size:.71rem; font-weight:750; background:#E4F6EF; color:#147459; }
.ss-status.missing { background:#FFF1DF; color:#966016; }
.ss-personal-shift { background:#FFFFFF; border:1px solid #E1EAF3; border-radius:16px; padding:1rem 1.15rem; margin-bottom:.7rem; min-height:108px; box-shadow:0 3px 15px rgba(20,45,78,.035); }
.ss-personal-shift .ss-date { color:#142D4E; font-size:.94rem; font-weight:800; }
.ss-personal-shift .ss-time { color:#60758B; font-size:.81rem; margin-top:.65rem; }
.ss-welcome { background:#F0F8F8; color:#166A71; border:1px solid #D5ECEB; border-radius:12px; padding:.7rem 1rem; margin:.4rem 0; font-weight:650; font-size:.9rem; }
@media (max-width: 768px) { .ss-hero { padding:1.4rem 1.15rem; } .ss-hero h2 { font-size:1.55rem; } .ss-panel { padding:.9rem; } }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Authentication and isolated public demo sessions
# --------------------------------------------------


def start_demo(initial_view):
    # Each browser session gets a separate writable copy of demo data.
    demo_engine, demo_path = create_demo_engine()
    st.session_state["demo_engine"] = demo_engine
    st.session_state["demo_database_path"] = demo_path
    st.session_state["demo_active"] = True
    st.session_state["demo_view"] = initial_view


def exit_demo():
    # Explicitly dispose and delete the temporary database on exit.
    demo_engine = st.session_state.pop("demo_engine", None)
    demo_path = st.session_state.pop("demo_database_path", None)
    if demo_engine is not None:
        demo_engine.dispose()
    if demo_path is not None:
        demo_path.unlink(missing_ok=True)
    # Remove previews and form/widget state that may refer to the old DB.
    st.session_state.clear()


if st.user.is_logged_in:
    # Google login grants no permissions by itself; check the allowlist.
    logged_in_email = st.user.get("email", "").strip().lower()
    manager_emails = {
        email.strip().lower()
        for email in st.secrets["roles"]["manager_emails"]
    }
    if not logged_in_email or logged_in_email not in manager_emails:
        st.error("Access denied. This account is not authorized.")
        st.button("🚪 Log out", on_click=st.logout)
        st.stop()

    user_role = "manager"
    active_engine = None  # Authorized local manager uses the existing DB.
    st.sidebar.button("🚪 Log out", on_click=st.logout)

else:
    user_role = "demo"
    if not st.session_state.get("demo_active", False):
        st.markdown(
            '<div class="ss-hero">'
            '<div class="ss-kicker">SMART WORKFORCE SCHEDULING</div>'
            '<h2>Better shifts. Happier teams.</h2>'
            '<p>Plan weekly schedules, balance employee availability, '
            'and resolve staffing gaps with optimization-powered tools.</p>'
            '</div>',
            unsafe_allow_html=True
        )
        st.divider()
        st.markdown(
            '<div class="ss-section"><h3>Explore SmartShift</h3>'
            '<p>Choose a role and explore a fully interactive, private demo.</p></div>',
            unsafe_allow_html=True
        )

        col_manager, col_employee = st.columns(2)
        with col_manager:
            with st.container(border=True):
                st.markdown("### 👩‍💼 Manager Demo")
                st.write("Create schedules, optimize staffing, publish weekly plans and manage coverage gaps.")
                if st.button("Explore Manager Demo", use_container_width=True):
                    try:
                        start_demo("Manager Dashboard")
                    except (OSError, ValueError) as error:
                        st.error(f"Could not start demo: {error}")
                    else:
                        st.rerun()
        with col_employee:
            with st.container(border=True):
                st.markdown("### 👩‍💻 Employee Demo")
                st.write("Review assigned shifts, submit availability and respond to staffing requests.")
                if st.button("Explore Employee Demo", use_container_width=True):
                    try:
                        start_demo("Employee Portal")
                    except (OSError, ValueError) as error:
                        st.error(f"Could not start demo: {error}")
                    else:
                        st.rerun()

        st.caption("🧪 Every visitor receives an independent set of fictional demo data.")
        st.markdown(
            '<div class="ss-section"><h3>Built for real scheduling challenges</h3>'
            '<p>Optimization with Google OR-Tools · Python · Streamlit · SQLAlchemy · SQLite</p>'
            '</div>', unsafe_allow_html=True
        )
        st.divider()
        st.subheader("Authorized Access")
        if st.button("🔐 Sign in with Google", use_container_width=True):
            st.login()
        st.stop()

    # Fail closed: never fall back to the shared database in demo mode.
    active_engine = st.session_state.get("demo_engine")
    if active_engine is None:
        st.error("The demo session could not be loaded. Please restart it.")
        st.stop()
    st.sidebar.caption("🧪 Isolated Demo Mode")
    st.sidebar.button("↩ Exit Demo", on_click=exit_demo)


# --------------------------------------------------
# Load data from SQLite
# --------------------------------------------------

# active_engine is selected above, after authentication/demo setup.

employees = [
    employee_from_db(row)
    for row in get_all_employees(db_engine=active_engine)
]

shifts = [
    shift_from_db(row)
    for row in get_all_shifts(db_engine=active_engine)
]

availabilities = [
    availability_from_db(row)
    for row in get_all_availabilities(db_engine=active_engine)
]

assignments = [
    assignment_from_db(row)
    for row in get_all_assignments(db_engine=active_engine)
]

staffing_requests = get_all_staffing_requests(
    db_engine=active_engine
)


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

st.sidebar.markdown("### 📅 SmartShift")
st.sidebar.caption("WORKFORCE MANAGEMENT")

# Secure accounts are manager-only; demo visitors can explore both views.
if user_role == "manager":
    view = "Manager Dashboard"
else:
    view = st.sidebar.radio(
        "Demo Navigation",
        ["Manager Dashboard", "Employee Portal"],
        key="demo_view"
    )


# --------------------------------------------------
# Manager Dashboard
# --------------------------------------------------

if view == "Manager Dashboard":

    st.markdown(
        '<div class="ss-hero">'
        '<div class="ss-kicker">MANAGER WORKSPACE · SMARTSHIFT</div>'
        '<h2>Workforce overview</h2>'
        '<p>Your scheduling command center — balance capacity, '
        'optimize shifts and keep your team in sync.</p>'
        '</div>',
        unsafe_allow_html=True
    )
    # ----------------------------------------------
    # Weekly dashboard statistics
    # ----------------------------------------------

    # Default to the most recent populated week so the dashboard has
    # meaningful content immediately; respect the user's chosen week.
    initial_schedule_date = (
        max(shift.date for shift in shifts)
        if shifts else date.today()
    )
    dashboard_date = st.session_state.get(
        "schedule_week_date",
        initial_schedule_date
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


    st.markdown(
        '<div class="ss-section"><h3>At a glance</h3>'
        '<p>Key indicators for the selected scheduling week</p></div>',
        unsafe_allow_html=True
    )
    st.caption(
        f"📅 Week of {dashboard_week_start:%d %b} – "
        f"{dashboard_week_end:%d %b %Y}"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Employees", total_employees)
    col2.metric("📅 Weekly Shifts", total_shifts)
    col3.metric("✅ Assigned Slots", f"{assigned_slots}/{required_slots}")
    col4.metric("⚠️ Staffing Gaps", missing_employees)

    # Top-of-page visual schedule summary. Detail controls remain below.
    st.markdown(
        '<div class="ss-section"><h3>Weekly schedule</h3>'
        '<p>Coverage at a glance · Morning and evening shifts</p></div>',
        unsafe_allow_html=True
    )
    if not dashboard_shifts:
        st.info("No shifts for this week yet. Use Create Weekly Shifts below.")
    else:
        from html import escape as _escape
        day_columns = st.columns(4)
        for day_offset in range(7):
            current_day = dashboard_week_start + timedelta(days=day_offset)
            day_shifts = sorted(
                (shift for shift in dashboard_shifts if shift.date == current_day),
                key=lambda item: item.start_time
            )
            if not day_shifts:
                continue
            shift_lines = []
            for shift in day_shifts:
                assigned = sum(
                    1 for assignment in dashboard_assignments
                    if assignment.shift_id == shift.shift_id
                )
                covered = assigned >= shift.required_employees
                kind = "Morning" if shift.start_time.hour < 12 else "Evening"
                chip_class = "ss-chip" if covered else "ss-chip missing"
                chip_text = "Covered" if covered else "Needs staff"
                shift_lines.append(
                    '<div class="ss-shift-line">'
                    f'<span>{_escape(kind)} · {shift.start_time:%H:%M}</span>'
                    f'<span class="{chip_class}">{assigned}/{shift.required_employees}'
                    f' · {chip_text}</span></div>'
                )
            card = (
                '<div class="ss-shift-card">'
                f'<div class="ss-shift-date">{current_day:%a · %d %b}</div>'
                + ''.join(shift_lines) + '</div>'
            )
            with day_columns[day_offset % 4]:
                st.markdown(card, unsafe_allow_html=True)
    st.caption("Select a different week under Generate Weekly Schedule to update this overview.")


    # ----------------------------------------------
    # Create weekly shifts
    # ----------------------------------------------

    with st.expander("📅 Create Weekly Shifts · Configure staffing", expanded=False):
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
                    staffing_requirements=staffing_requirements,
                    db_engine=active_engine
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
    # Weekly availability deadline
    # ----------------------------------------------

    st.divider()
    with st.expander("⏰ Weekly Availability Deadline", expanded=False):

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
            deadline_week_start,
            db_engine=active_engine
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
                    deadline_time=deadline_time,
                    db_engine=active_engine
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
    # Weekly availability tracking
    # ----------------------------------------------

    with st.expander("📋 Availability Tracking · Team submissions", expanded=False):
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


    st.markdown(
        '<div class="ss-section"><h3>✨ Generate weekly schedule</h3>'
        '<p>Build and review an optimization-powered weekly proposal</p></div>',
        unsafe_allow_html=True
    )
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
        value=initial_schedule_date,
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
        week_start,
        db_engine=active_engine
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
                    week_start=week_start,
                    db_engine=active_engine
                )
            )
            st.session_state.preview_week_start = week_start
            st.session_state.preview_fingerprint = (
                get_weekly_schedule_fingerprint(
                    week_start=week_start,
                    db_engine=active_engine
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
    st.markdown(
        '<div class="ss-section"><h3>🗓️ Detailed schedule</h3>'
        '<p>Review shift assignments by day or in a table</p></div>',
        unsafe_allow_html=True
    )

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


    cards_tab, table_tab = st.tabs(
        ["📱 Daily View", "📊 Table View"]
    )

    with cards_tab:
        detail_columns = st.columns(2)
        for day_index, row in enumerate(weekly_grid_rows):
            day_label = html_escape(row["Day"])
            slots_html = []
            for icon, title, key in (
                ("☀️", "Morning · 08:00–16:00", "Morning 08:00–16:00"),
                ("🌙", "Evening · 16:00–23:00", "Evening 16:00–23:00"),
            ):
                description = html_escape(row[key])
                slots_html.append(
                    '<div class="ss-slot">'
                    f'<div class="ss-slot-title">{icon} {title}</div>'
                    f'<div class="ss-slot-names">{description}</div>'
                    '</div>'
                )
            with detail_columns[day_index % 2]:
                st.markdown(
                    '<div class="ss-panel">'
                    f'<div class="ss-day-title">📅 {day_label}</div>'
                    + "".join(slots_html) + '</div>',
                    unsafe_allow_html=True
                )

    with table_tab:
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
                    db_engine=active_engine,
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
        publish_week_start,
        db_engine=active_engine
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
                    publish_week_start,
                    db_engine=active_engine
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
    # Calculate gaps for the selected week,
    # including saved and proposed assignments.
    weekly_shifts = [
        shift
        for shift in shifts
        if week_start <= shift.date < week_start + timedelta(days=7)
    ]

    weekly_gaps = find_staffing_gaps(
        weekly_shifts,
        preview
    )

    if not weekly_gaps:

        st.success(
            "All shifts are fully staffed!"
        )

    else:

        for gap in weekly_gaps:

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
                weekly_shifts,
                preview
            )

            ranked = rank_eligible_employees(
                eligible,
                preview
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
                        for assignment in preview
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
                            shift.shift_id,
                            db_engine=active_engine
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

    weekly_shift_ids = {
        shift.shift_id
        for shift in weekly_shifts
    }

    weekly_staffing_requests = [
        request
        for request in staffing_requests
        if request.shift_id in weekly_shift_ids
    ]

    if not weekly_staffing_requests:

        st.info(
            "No staffing requests yet."
        )

    else:

        request_rows = []


        weekly_shift_lookup = {
            shift.shift_id: shift
            for shift in weekly_shifts
        }

        for request in weekly_staffing_requests:
            shift = weekly_shift_lookup.get(request.shift_id)

            if shift is None:
                continue

            shift_type = (
                "Morning"
                if shift.start_time.hour < 12
                else "Evening"
            )

            request_rows.append({
                "Employee": employee_names.get(
                    request.employee_id,
                    "Unknown"
                ),
                "Date": shift.date.strftime("%d/%m/%Y"),
                "Shift": shift_type,
                "Status": request.status.capitalize()
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

    st.markdown(
        '<div class="ss-hero">'
        '<div class="ss-kicker">EMPLOYEE WORKSPACE · SMARTSHIFT</div>'
        '<h2>Your shifts, simplified.</h2>'
        '<p>See your schedule, share availability and respond to requests '
        'in one convenient place.</p></div>',
        unsafe_allow_html=True
    )
    st.caption(
        "Demo profile switching is for sample data only — "
        "not employee authentication."
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

    st.markdown(
        f'<div class="ss-welcome">👋 Welcome, {html_escape(selected_name)}. '
        'Your week, all in one place.</div>',
        unsafe_allow_html=True
    )

    # Employee IDs remain internal and are not displayed in the portal.

    # ----------------------------------------------

    # ----------------------------------------------
    # My Weekly Availability
    # ----------------------------------------------

    st.markdown(
        '<div class="ss-section"><h3>My workspace</h3>'
        '<p>Choose a week to view your shifts, requests and availability.</p></div>',
        unsafe_allow_html=True
    )

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

    # Employee overview: built from the selected employee and week only.
    selected_week_shift_ids = {shift.shift_id for shift in weekly_shifts}
    selected_week_assignments = [
        assignment for assignment in assignments
        if assignment.employee_id == selected_employee_id
        and assignment.shift_id in selected_week_shift_ids
    ]
    selected_week_pending = [
        request for request in staffing_requests
        if request.employee_id == selected_employee_id
        and request.shift_id in selected_week_shift_ids
        and request.status == "pending"
    ]
    submitted_for_week = sum(
        1 for shift in weekly_shifts
        if shift.shift_id in employee_availability_lookup
    )
    st.markdown(
        '<div class="ss-section"><h3>Your weekly snapshot</h3>'
        '<p>Personal scheduling overview for the selected week</p></div>',
        unsafe_allow_html=True
    )
    employee_col1, employee_col2, employee_col3 = st.columns(3)
    employee_col1.metric("📅 Assigned shifts", len(selected_week_assignments))
    employee_col2.metric(
        "✅ Availability submitted",
        f"{submitted_for_week}/{len(weekly_shifts)}"
    )
    employee_col3.metric("📩 Pending requests", len(selected_week_pending))
    if selected_week_pending:
        st.warning(
            f"You have {len(selected_week_pending)} pending staffing request(s). "
            "Review them in My Staffing Requests below."
        )

    # ----------------------------------------------
    # My assigned shifts
    # ----------------------------------------------

    st.markdown(
        '<div class="ss-section"><h3>📅 My assigned shifts</h3>'
        '<p>Your published shift plan for the selected week</p></div>',
        unsafe_allow_html=True
    )

    # Show only assignments from the selected week
    weekly_shift_ids = {
        shift.shift_id
        for shift in weekly_shifts
    }

    # Employees can view only published schedules.
    employee_schedule_status = get_weekly_schedule_status(
        availability_week_start,
        db_engine=active_engine
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

        total_minutes = 0

        for assignment in my_assignments:

            shift = next(

                (

                    s for s in weekly_shifts

                    if s.shift_id == assignment.shift_id

                ),

                None

            )

            if shift is None:
                continue

            start = shift.start_time

            end = shift.end_time

            shift_minutes = (

                    end.hour * 60 + end.minute

                    - start.hour * 60 - start.minute

            )

            total_minutes += shift_minutes

            shift_type = (

                "Morning"

                if start.hour < 12

                else "Evening"

            )

            my_shift_rows.append({

                "Day": shift.date.strftime("%A"),

                "Date": shift.date.strftime("%d/%m/%Y"),

                "Shift": shift_type,

                "Working Hours": (

                    f"{start.strftime('%H:%M')}–"

                    f"{end.strftime('%H:%M')}"

                ),

                "_sort_date": shift.date,

                "_sort_time": start

            })

        # Sort shifts by date and start time.

        my_shift_rows.sort(

            key=lambda row: (

                row["_sort_date"],

                row["_sort_time"]

            )

        )

        # Remove internal sorting fields from the display.

        display_rows = [

            {

                key: value

                for key, value in row.items()

                if not key.startswith("_")

            }

            for row in my_shift_rows

        ]

        total_hours = total_minutes / 60

        st.caption(f"{len(display_rows)} shifts · {total_hours:g} scheduled hours")
        personal_columns = st.columns(2)
        for shift_index, shift_row in enumerate(display_rows):
            with personal_columns[shift_index % 2]:
                st.markdown(
                    '<div class="ss-personal-shift">'
                    f'<div class="ss-date">📅 {html_escape(shift_row["Day"])} · '
                    f'{html_escape(shift_row["Date"])}</div>'
                    f'<div class="ss-time">🕒 {html_escape(shift_row["Shift"])} · '
                    f'{html_escape(shift_row["Working Hours"])}</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

    # ----------------------------------------------
    # My staffing requests from SQLite
    # ----------------------------------------------

    st.markdown(
        '<div class="ss-section"><h3>📩 Staffing requests</h3>'
        '<p>Review invitations and respond when coverage is needed</p></div>',
        unsafe_allow_html=True
    )

    # Show requests for the selected week only.
    weekly_shift_lookup = {
        shift.shift_id: shift
        for shift in weekly_shifts
    }

    my_requests = [
        request
        for request in staffing_requests
        if request.employee_id == selected_employee_id
        and request.shift_id in weekly_shift_lookup
    ]

    if not my_requests:
        st.info(
            "You have no staffing requests for this week."
        )

    else:
        request_rows = []

        for request in my_requests:
            shift = weekly_shift_lookup[request.shift_id]

            shift_type = (
                "Morning"
                if shift.start_time.hour < 12
                else "Evening"
            )

            request_rows.append({
                "Day": shift.date.strftime("%A"),
                "Date": shift.date.strftime("%d/%m/%Y"),
                "Shift": shift_type,
                "Working Hours": (
                    f"{shift.start_time.strftime('%H:%M')}–"
                    f"{shift.end_time.strftime('%H:%M')}"
                ),
                "Status": request.status.capitalize(),
                "_sort_date": shift.date,
                "_sort_time": shift.start_time
            })

        # Display requests in chronological order.
        request_rows.sort(
            key=lambda row: (
                row["_sort_date"],
                row["_sort_time"]
            )
        )

        display_rows = [
            {
                key: value
                for key, value in row.items()
                if not key.startswith("_")
            }
            for row in request_rows
        ]

        st.dataframe(
            display_rows,
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




            # Look up shift details for pending requests.
            shift_lookup = {
                shift.shift_id: shift
                for shift in shifts
            }

            for request in pending_requests:
                shift = shift_lookup.get(request.shift_id)

                if shift is None:
                    st.warning(
                        "Shift details are unavailable "
                        "for this request."
                    )
                    continue

                shift_type = (
                    "Morning"
                    if shift.start_time.hour < 12
                    else "Evening"
                )

                with st.container(border=True):
                    st.markdown("#### 📩 New Staffing Request")

                    st.write(
                        f"📅 **{shift.date.strftime('%A, %d/%m/%Y')}**"
                    )

                    st.write(
                        f"🕒 **{shift_type} Shift** · "
                        f"{shift.start_time.strftime('%H:%M')}–"
                        f"{shift.end_time.strftime('%H:%M')}"
                    )

                    st.caption(
                        "You've been invited to cover this shift."
                    )

                    col_accept, col_decline = st.columns(2)

                    with col_accept:
                        if st.button(
                            "✅ Accept",
                            key=f"accept_{request.request_id}",
                            use_container_width=True
                        ):
                            try:
                                accept_and_assign_request(
                                    request.request_id,
                                    db_engine=active_engine
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
                            key=f"decline_{request.request_id}",
                            use_container_width=True
                        ):
                            try:
                                decline_staffing_request(
                                    request.request_id,
                                    db_engine=active_engine
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

    st.markdown(
        '<div class="ss-section"><h3>✅ Manage availability</h3>'
        '<p>Update your preferences when the submission window is open</p></div>',
        unsafe_allow_html=True
    )
    with st.expander(f"✏️ Edit weekly availability · {len(weekly_shifts)} shifts", expanded=False):
        # ----------------------------------------------
        # Weekly availability deadline status
        # ----------------------------------------------


        employee_week_deadline = get_weekly_deadline(
            availability_week_start,
            db_engine=active_engine
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

                    shift_label = (
                        "Morning" if shift.start_time.hour < 12
                        else "Evening"
                    )
                    st.write(
                        f"**{shift.date:%A, %d/%m/%Y} · "
                        f"{shift_label}**  "
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
                            shift_statuses=shift_statuses,
                            db_engine=active_engine
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

