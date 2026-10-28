
import streamlit as st

from sample_data import (
    create_sample_employees,
    create_sample_shifts,
    create_sample_availabilities
)
from scheduler import generate_schedule
from staffing import find_staffing_gaps
from recommendations import (
    find_flexible_employees,
    filter_eligible_employees,
    rank_eligible_employees
)
from staffing_request import (
    StaffingRequest,
    RequestStatus,
    apply_approved_request
)
from availability import AvailabilityStatus


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="SmartShift",
    page_icon="📅",
    layout="wide"
)


# --------------------------------------------------
# Initialize demo data
# --------------------------------------------------

if "staffing_requests" not in st.session_state:
    st.session_state.staffing_requests = []

if "next_request_id" not in st.session_state:
    st.session_state.next_request_id = 1

if "employees" not in st.session_state:
    st.session_state.employees = create_sample_employees()

if "shifts" not in st.session_state:
    st.session_state.shifts = create_sample_shifts()

if "availabilities" not in st.session_state:
    st.session_state.availabilities = create_sample_availabilities(
        st.session_state.employees,
        st.session_state.shifts
    )


# Repair demo data saved with an older enum definition
availabilities = st.session_state.availabilities

if st.sidebar.button("Reset Demo Data"):
    for key in [
        "employees",
        "shifts",
        "availabilities",
        "staffing_requests",
        "next_request_id"
    ]:
        st.session_state.pop(key, None)

    st.rerun()


has_old_status_objects = any(
    not isinstance(availability.status, AvailabilityStatus)
    for availability in availabilities
)

if has_old_status_objects:
    st.session_state.availabilities = create_sample_availabilities(
        st.session_state.employees,
        st.session_state.shifts
    )


# Get current data from session state
employees = st.session_state.employees
shifts = st.session_state.shifts
availabilities = st.session_state.availabilities


# --------------------------------------------------
# Generate schedule and find gaps
# --------------------------------------------------

assignments = generate_schedule(
    employees,
    shifts,
    availabilities
)

gaps = find_staffing_gaps(
    shifts,
    assignments
)


# --------------------------------------------------
# Navigation
# --------------------------------------------------

st.title("📅 SmartShift")

view = st.sidebar.radio(
    "Navigation",
    ["Manager Dashboard", "Employee Portal"]
)


# --------------------------------------------------
# Manager Dashboard
# --------------------------------------------------

if view == "Manager Dashboard":

    st.subheader("Manager Dashboard")
    st.write("Overview of your weekly employee schedule")

    # Dashboard statistics
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

    col1.metric("Employees", total_employees)
    col2.metric("Total Shifts", total_shifts)

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

        missing = shift.required_employees - assigned_count

        schedule_rows.append({
            "Shift ID": shift.shift_id,
            "Date": shift.date.strftime("%d/%m/%Y"),
            "Start": shift.start_time.strftime("%H:%M"),
            "End": shift.end_time.strftime("%H:%M"),
            "Required": shift.required_employees,
            "Assigned": assigned_count,
            "Status": (
                "✅ Covered"
                if missing == 0
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
        st.success("All shifts are fully staffed!")

    else:
        for gap in gaps:
            shift = next(
                s for s in shifts
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
                        "Preferred Shifts": employee.preferred_shifts,
                        "Maximum Shifts": employee.max_shifts
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
                    key=f"employee_select_{shift.shift_id}"
                )

                # Send request
                if st.button(
                    "Send Request",
                    key=f"send_request_{shift.shift_id}"
                ):
                    employee_id = employee_options[
                        selected_employee_name
                    ]

                    existing_request = any(
                        request.employee_id == employee_id
                        and request.shift_id == shift.shift_id
                        for request in st.session_state.staffing_requests
                    )

                    if existing_request:
                        st.warning(
                            "A request already exists for "
                            "this employee and shift."
                        )

                    else:
                        request = StaffingRequest(
                            st.session_state.next_request_id,
                            employee_id,
                            shift.shift_id
                        )

                        st.session_state.staffing_requests.append(
                            request
                        )

                        st.session_state.next_request_id += 1

                        st.success(
                            f"Request created for "
                            f"{selected_employee_name}!"
                        )

    # ----------------------------------------------
    # Staffing requests
    # ----------------------------------------------

    st.divider()
    st.subheader("Staffing Requests")

    if not st.session_state.staffing_requests:
        st.info("No staffing requests yet.")

    else:
        employee_names = {
            employee.employee_id: employee.name
            for employee in employees
        }

        request_rows = []

        for request in st.session_state.staffing_requests:
            request_rows.append({
                "Request ID": request.request_id,
                "Employee": employee_names.get(
                    request.employee_id,
                    "Unknown"
                ),
                "Shift ID": request.shift_id,
                "Status": request.status.value
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

    st.write("View your shifts and staffing requests.")

    employee_options = {
        employee.name: employee.employee_id
        for employee in employees
    }

    selected_name = st.selectbox(
        "Select employee",
        options=list(employee_options.keys())
    )

    selected_employee_id = employee_options[selected_name]

    st.success(f"Welcome, {selected_name}!")

    st.write(
        f"Employee ID: {selected_employee_id}"
    )

    st.divider()
    st.subheader("My Staffing Requests")

    my_requests = [
        request
        for request in st.session_state.staffing_requests
        if request.employee_id == selected_employee_id
    ]

    if not my_requests:
        st.info("You have no staffing requests.")

    else:
        request_rows = []

        for request in my_requests:
            request_rows.append({
                "Request ID": request.request_id,
                "Shift ID": request.shift_id,
                "Status": request.status.value
            })

        st.dataframe(
            request_rows,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Respond to Requests")

        for request in my_requests:
            if request.status == RequestStatus.PENDING:
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
                        request.accept()

                        apply_approved_request(
                            request,
                            st.session_state.availabilities
                        )

                        st.rerun()


                with col_decline:
                    if st.button(
                        "❌ Decline",
                        key=f"decline_{request.request_id}"
                    ):
                        request.decline()
                        st.rerun()



