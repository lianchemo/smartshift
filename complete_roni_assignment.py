
from database.assignment_service import assign_accepted_request


try:
    assign_accepted_request(1)
    print("SUCCESS: Roni was assigned to shift 213!")

except ValueError as error:
    print("Assignment failed:", error)
