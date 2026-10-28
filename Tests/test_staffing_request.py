
import pytest

from staffing_request import StaffingRequest, RequestStatus
from availability import Availability, AvailabilityStatus
from staffing_request import apply_approved_request


def test_new_request_is_pending():
    request = StaffingRequest(1, 107, 213)

    assert request.status == RequestStatus.PENDING


def test_request_can_be_accepted():
    request = StaffingRequest(1, 107, 213)

    request.accept()

    assert request.status == RequestStatus.ACCEPTED


def test_declined_request_cannot_be_accepted():
    request = StaffingRequest(1, 107, 213)

    request.decline()

    with pytest.raises(ValueError):
        request.accept()

    assert request.status == RequestStatus.DECLINED

def test_approved_request_updates_availability():
    availability = Availability(
        107, 213, AvailabilityStatus.FLEXIBLE
    )

    request = StaffingRequest(1, 107, 213)
    request.accept()

    apply_approved_request(request, [availability])

    assert availability.status == AvailabilityStatus.AVAILABLE

def test_pending_request_cannot_update_availability():
    availability = Availability(
        107, 213, AvailabilityStatus.FLEXIBLE
    )

    request = StaffingRequest(1, 107, 213)

    with pytest.raises(ValueError):
        apply_approved_request(request, [availability])

    assert availability.status == AvailabilityStatus.FLEXIBLE
