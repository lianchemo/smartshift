
from database.staffing_request_repository import (
    add_staffing_request,
    get_all_staffing_requests,
    update_request_status
)


# Create a request for Roni, shift 213
request_id = add_staffing_request(107, 213)

print("\nStaffing requests in database:")

for request in get_all_staffing_requests():
    print(
        request.request_id,
        request.employee_id,
        request.shift_id,
        request.status
    )

request = next(
    r for r in get_all_staffing_requests()
    if r.request_id == request_id
)

if request.status == "pending":
    update_request_status(request_id, "accepted")
else:
    print("Request was already handled.")

print("\nUpdated request status:")

for request in get_all_staffing_requests():
    if request.request_id == request_id:
        print(request.request_id, request.status)

