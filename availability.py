
from enum import Enum


class AvailabilityStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FLEXIBLE = "flexible"


class Availability:
    def __init__(self, employee_id, shift_id, status):
        if not isinstance(status, AvailabilityStatus):
            raise TypeError("status must be an AvailabilityStatus")

        self.employee_id = employee_id
        self.shift_id = shift_id
        self.status = status

    def __str__(self):
        return (
            f"Employee {self.employee_id} | "
            f"Shift {self.shift_id} | "
            f"Status: {self.status.value}"
        )
