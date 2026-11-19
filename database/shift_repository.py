
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import engine
from database.models import ShiftDB



def add_shift(shift, db_engine=None):
    active_engine = db_engine if db_engine is not None else engine

    with Session(active_engine) as session:

        existing_shift = session.get(
            ShiftDB,
            shift.shift_id
        )

        if existing_shift is not None:
            print(f"Shift {shift.shift_id} already exists.")
            return

        db_shift = ShiftDB(
            shift_id=shift.shift_id,
            date=shift.date,
            start_time=shift.start_time,
            end_time=shift.end_time,
            required_employees=shift.required_employees
        )

        session.add(db_shift)
        session.commit()

        print(f"Shift {shift.shift_id} saved successfully!")



def add_shifts(shifts, db_engine=None):
    for shift in shifts:
        add_shift(shift, db_engine=db_engine)




def get_all_shifts(db_engine=None):
    active_engine = db_engine if db_engine is not None else engine

    with Session(active_engine) as session:

        statement = select(ShiftDB).order_by(
            ShiftDB.date,
            ShiftDB.start_time
        )

        return session.scalars(statement).all()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from sample_data import create_sample_shifts

    shifts = create_sample_shifts()

    add_shifts(shifts)

    print("\nShifts stored in database:")

    for shift in get_all_shifts():
        print(
            shift.shift_id,
            shift.date,
            shift.start_time,
            shift.end_time,
            f"Required: {shift.required_employees}"
        )
