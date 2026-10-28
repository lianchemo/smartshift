
from datetime import date, time


class Shift:
    def __init__(self, shift_id, shift_date, start_time, end_time, required_employees):

        if not isinstance(shift_date, date):
            raise TypeError("shift_date must be a date")

        if not isinstance(start_time, time) or not isinstance(end_time, time):
            raise TypeError("Start and end times must be time objects")

        if start_time >= end_time:
            raise ValueError("Start time must be before end time")

        if not isinstance(required_employees, int) or isinstance(required_employees, bool):
            raise TypeError("required_employees must be an integer")

        if required_employees <= 0:
            raise ValueError("Required employees must be greater than zero")

        self.shift_id = shift_id
        self.date = shift_date
        self.start_time = start_time
        self.end_time = end_time
        self.required_employees = required_employees

    def __str__(self):
        return (
            f"Shift {self.shift_id} | "
            f"{self.date} | "
            f"{self.start_time.strftime('%H:%M')}-"
            f"{self.end_time.strftime('%H:%M')} | "
            f"Required employees: {self.required_employees}"
        )
