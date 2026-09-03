"""
In-memory "data access" layer.

All employee records live in a plain Python list for the duration of the
process. There is no database in this stage of the project, so data resets
whenever the app restarts. Keeping this logic in its own module (rather than
inline in main.py) means it can be swapped for a real database layer later
without touching the route handlers themselves.
"""

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from app.schemas import Employee, EmployeeCreate, EmployeeUpdate


class EmployeeNotFoundError(Exception):
    """Raised when an employee with the given id does not exist."""

    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(f"Employee with id {employee_id} not found")


class DuplicateEmailError(Exception):
    """Raised when an email address is already used by another employee."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already registered")


class EmployeeService:
    """Holds the in-memory list of employees and the id counter.

    A lock guards mutations. FastAPI/Uvicorn normally runs a single worker
    with an async event loop, so true concurrent threads aren't usually in
    play, but the lock costs nothing and protects against edge cases (e.g.
    running with multiple threads) without adding real complexity.
    """

    def __init__(self) -> None:
        self._employees: list[Employee] = []
        self._next_id: int = 1
        self._lock = Lock()

    def _find_index(self, employee_id: int) -> Optional[int]:
        for index, employee in enumerate(self._employees):
            if employee.id == employee_id:
                return index
        return None

    def _email_taken(self, email: str, exclude_id: Optional[int] = None) -> bool:
        normalized = email.strip().lower()
        return any(
            emp.email.lower() == normalized
            for emp in self._employees
            if emp.id != exclude_id
        )

    def list_employees(self) -> list[Employee]:
        return list(self._employees)

    def get_employee(self, employee_id: int) -> Employee:
        index = self._find_index(employee_id)
        if index is None:
            raise EmployeeNotFoundError(employee_id)
        return self._employees[index]

    def create_employee(self, payload: EmployeeCreate) -> Employee:
        with self._lock:
            if self._email_taken(payload.email):
                raise DuplicateEmailError(payload.email)

            employee = Employee(
                id=self._next_id,
                created_at=datetime.now(timezone.utc),
                **payload.model_dump(),
            )
            self._employees.append(employee)
            self._next_id += 1
            return employee

    def update_employee(self, employee_id: int, payload: EmployeeUpdate) -> Employee:
        with self._lock:
            index = self._find_index(employee_id)
            if index is None:
                raise EmployeeNotFoundError(employee_id)

            if self._email_taken(payload.email, exclude_id=employee_id):
                raise DuplicateEmailError(payload.email)

            existing = self._employees[index]
            updated = Employee(
                id=existing.id,
                created_at=existing.created_at,
                **payload.model_dump(),
            )
            self._employees[index] = updated
            return updated

    def delete_employee(self, employee_id: int) -> None:
        with self._lock:
            index = self._find_index(employee_id)
            if index is None:
                raise EmployeeNotFoundError(employee_id)
            del self._employees[index]


# Module-level singleton used by the route handlers. Since the whole app
# runs as a single process with no database, one shared in-memory store is
# all that's needed for this stage.
employee_service = EmployeeService()
