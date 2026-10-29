
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import AssignmentDB


def add_assignments(assignments):
    added_count = 0

    with Session(engine) as session:
        for assignment in assignments:
            statement = select(AssignmentDB).where(
                AssignmentDB.employee_id == assignment.employee_id,
                AssignmentDB.shift_id == assignment.shift_id
            )

            existing = session.scalar(statement)

            if existing is not None:
                continue

            db_assignment = AssignmentDB(
                employee_id=assignment.employee_id,
                shift_id=assignment.shift_id
            )

            session.add(db_assignment)
            added_count += 1

        session.commit()

    print(f"Added {added_count} assignments.")


def get_all_assignments():
    with Session(engine) as session:
        statement = select(AssignmentDB).order_by(
            AssignmentDB.shift_id,
            AssignmentDB.employee_id
        )

        return session.scalars(statement).all()
