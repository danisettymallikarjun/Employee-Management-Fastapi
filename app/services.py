"""
Database service layer for employee records using SQLAlchemy.
"""

from typing import Any, Optional
# Keep the service usable when SQLAlchemy's ORM stubs are unavailable to the
# type checker; the concrete session is supplied by the application at runtime.
Session = Any

from app.models import EmployeeModel
from app.schemas import EmployeeCreate, EmployeeUpdate


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
    """SQLAlchemy-backed CRUD service for employee records."""

    @staticmethod
    def list_employees(db: Session) -> list[EmployeeModel]:
        """Fetch all employees from the MySQL database."""
        return db.query(EmployeeModel).all()

    @staticmethod
    def get_employee(db: Session, employee_id: int) -> EmployeeModel:
        """Fetch a single employee by ID from MySQL."""
        employee = db.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        if employee is None:
            raise EmployeeNotFoundError(employee_id)
        return employee

    @staticmethod
    def get_employee_by_email(
        db: Session, email: str, exclude_id: Optional[int] = None
    ) -> Optional[EmployeeModel]:
        """Check if an email already exists (case-insensitive)."""
        query = db.query(EmployeeModel).filter(
            EmployeeModel.email.ilike(email.strip())
        )
        if exclude_id is not None:
            query = query.filter(EmployeeModel.id != exclude_id)
        return query.first()

    @staticmethod
    def create_employee(db: Session, payload: EmployeeCreate) -> EmployeeModel:
        """Create a new employee record in MySQL."""
        if EmployeeService.get_employee_by_email(db, payload.email):
            raise DuplicateEmailError(payload.email)

        employee = EmployeeModel(
            name=payload.name,
            email=payload.email.strip().lower(),
            department=payload.department,
            primary_skill=payload.primary_skill,
            location=payload.location,
            work_mode=payload.work_mode.value,
            is_active=payload.is_active,
        )
        try:
            db.add(employee)
            db.commit()
            db.refresh(employee)
            return employee
        except Exception as error:
            db.rollback()
            if error.__class__.__name__ == "IntegrityError":
                raise DuplicateEmailError(payload.email) from error
            raise

    @staticmethod
    def update_employee(
        db: Session, employee_id: int, payload: EmployeeUpdate
    ) -> EmployeeModel:
        """Update an existing employee record, preserving created_at."""
        employee = EmployeeService.get_employee(db, employee_id)
        if EmployeeService.get_employee_by_email(
            db, payload.email, exclude_id=employee_id
        ):
            raise DuplicateEmailError(payload.email)

        employee.name = payload.name
        employee.email = payload.email.strip().lower()
        employee.department = payload.department
        employee.primary_skill = payload.primary_skill
        employee.location = payload.location
        employee.work_mode = payload.work_mode.value
        employee.is_active = payload.is_active
        # created_at is preserved

        try:
            db.commit()
            db.refresh(employee)
            return employee
        except Exception as error:
            db.rollback()
            if error.__class__.__name__ == "IntegrityError":
                raise DuplicateEmailError(payload.email) from error
            raise

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> None:
        """Delete an employee record from MySQL."""
        employee = EmployeeService.get_employee(db, employee_id)
        try:
            db.delete(employee)
            db.commit()
        except Exception:
            db.rollback()
            raise
