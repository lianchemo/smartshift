from datetime import date, time
from sqlalchemy import (
    Integer,
    String,
    Date,
    Time,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EmployeeDB(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    max_shifts: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    preferred_shifts: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

class ShiftDB(Base):
    __tablename__ = "shifts"

    shift_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False
    )

    required_employees: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

class AvailabilityDB(Base):
    __tablename__ = "availabilities"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "shift_id",
            name="uq_employee_shift_availability"
        ),
    )

    availability_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.shift_id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

class AssignmentDB(Base):
    __tablename__ = "assignments"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "shift_id",
            name="uq_employee_shift_assignment"
        ),
    )

    assignment_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.shift_id"),
        nullable=False
    )

class StaffingRequestDB(Base):
    __tablename__ = "staffing_requests"

    request_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.shift_id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"
    )


