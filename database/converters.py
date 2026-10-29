from assignment import Assignment
from shift import Shift
from availability import Availability, AvailabilityStatus
from employee import Employee


def employee_from_db(db_employee):
    return Employee(
        employee_id=db_employee.employee_id,
        name=db_employee.name,
        max_shifts=db_employee.max_shifts,
        preferred_shifts=db_employee.preferred_shifts
    )

def shift_from_db(db_shift):
    return Shift(
        shift_id=db_shift.shift_id,
        shift_date=db_shift.date,
        start_time=db_shift.start_time,
        end_time=db_shift.end_time,
        required_employees=db_shift.required_employees
    )


def availability_from_db(db_availability):
    return Availability(
        employee_id=db_availability.employee_id,
        shift_id=db_availability.shift_id,
        status=AvailabilityStatus(db_availability.status)
    )

def assignment_from_db(db_assignment):
    return Assignment(
        employee_id=db_assignment.employee_id,
        shift_id=db_assignment.shift_id
    )


