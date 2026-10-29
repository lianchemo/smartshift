
from sqlalchemy.orm import Session

from database.db import engine
from database.models import EmployeeDB


def add_employee(employee_id, name, max_shifts, preferred_shifts):
    with Session(engine) as session:
        existing_employee = session.get(EmployeeDB, employee_id)

        if existing_employee is not None:
            print("Employee already exists.")
            return

        employee = EmployeeDB(
            employee_id=employee_id,
            name=name,
            max_shifts=max_shifts,
            preferred_shifts=preferred_shifts
        )

        session.add(employee)
        session.commit()

        print(f"Employee {name} saved successfully!")


def get_employee(employee_id):
    with Session(engine) as session:
        return session.get(EmployeeDB, employee_id)



def add_employees(employees):
    for employee in employees:
        add_employee(
            employee.employee_id,
            employee.name,
            employee.max_shifts,
            employee.preferred_shifts
        )


def get_all_employees():
    from sqlalchemy import select

    with Session(engine) as session:
        statement = select(EmployeeDB).order_by(
            EmployeeDB.employee_id
        )

        return session.scalars(statement).all()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Allow importing sample_data from the project root
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from sample_data import create_sample_employees

    employees = create_sample_employees()

    add_employees(employees)

    print("\nEmployees stored in database:")

    for employee in get_all_employees():
        print(employee.employee_id, employee.name)
