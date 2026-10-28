
class Employee:
    def __init__(self, employee_id, name, max_shifts, preferred_shifts):
        self.employee_id = employee_id
        self.name = name
        self.max_shifts = max_shifts
        self.preferred_shifts = preferred_shifts

    def __str__(self):
        return f"{self.name} (ID: {self.employee_id})"
