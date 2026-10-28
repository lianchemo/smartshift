
class Assignment:
    def __init__(self, employee_id, shift_id):
        self.employee_id = employee_id
        self.shift_id = shift_id

    def __str__(self):
        return (
            f"Employee {self.employee_id} "
            f"assigned to Shift {self.shift_id}"
        )
