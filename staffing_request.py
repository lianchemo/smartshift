
from enum import Enum


class RequestStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class StaffingRequest:
    def __init__(self, request_id, employee_id, shift_id):
        self.request_id = request_id
        self.employee_id = employee_id
        self.shift_id = shift_id
        self.status = RequestStatus.PENDING

    def accept(self):
        if self.status != RequestStatus.PENDING:
            raise ValueError("Only pending requests can be accepted")

        self.status = RequestStatus.ACCEPTED

    def decline(self):
        if self.status != RequestStatus.PENDING:
            raise ValueError("Only pending requests can be declined")

        self.status = RequestStatus.DECLINED

    def __str__(self):
        return (
            f"Request {self.request_id} | "
            f"Employee {self.employee_id} | "
            f"Shift {self.shift_id} | "
            f"Status: {self.status.value}"
        )


from availability import AvailabilityStatus


def apply_approved_request(request, availabilities):
    if request.status != RequestStatus.ACCEPTED:
        raise ValueError("Only accepted requests can be applied")

    for availability in availabilities:
        if (
            availability.employee_id == request.employee_id
            and availability.shift_id == request.shift_id
        ):
            if availability.status != AvailabilityStatus.FLEXIBLE:
                raise ValueError(
                    "Employee must be flexible for this shift"
                )

            availability.status = AvailabilityStatus.AVAILABLE
            return

    raise ValueError("Availability record not found")
