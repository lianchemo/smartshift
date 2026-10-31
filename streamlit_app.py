
import streamlit as st
from database.request_service import (
    accept_and_assign_request,
    decline_staffing_request
)
from database.employee_repository import get_all_employees
from database.shift_repository import get_all_shifts
from database.availability_repository import get_all_availabilities
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
    # Dashboard statistics
    # ----------------------------------------------

    total_employees = len(employees)
    total_shifts = len(shifts)
    assigned_slots = len(assignments)

    required_slots = sum(
        shift.required_employees
        for shift in shifts
    )

    missing_employees = sum(
        gap["missing"]
        for gap in gaps
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
    # Weekly shift schedule
    # ----------------------------------------------

    st.divider()

    st.subheader("Weekly Shift Schedule")

    schedule_rows = []

    for shift in shifts:

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
    # My assigned shifts
    # ----------------------------------------------

    st.divider()

    st.subheader("My Assigned Shifts")

    my_assignments = [
        assignment
        for assignment in assignments
        if assignment.employee_id
        == selected_employee_id
    ]

    if not my_assignments:

        st.info(
            "You have no assigned shifts."
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

