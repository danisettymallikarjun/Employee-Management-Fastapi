"""
Database service layer for employee records using SQLAlchemy.
"""

from sqlalchemy import func  # type: ignore[reportMissingImports]
from sqlalchemy.exc import IntegrityError  # type: ignore[reportMissingImports]
from typing import Any, Optional
# Keep the service usable when SQLAlchemy's ORM stubs are unavailable to the
# type checker; the concrete session is supplied by the application at runtime.
Session = Any

from app.models import EmployeeModel , WorkItemModel
from app.schemas import (EmployeeCreate, EmployeeUpdate , WorkMode, WorkItemCreate, WorkItemUpdate, 
                          WorkItemStatus, WorkItemPriority)
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

class WorkItemNotFoundError(Exception):
    """Raised when a work item with the given id does not exist."""
    
    def __init__(self, work_item_id: int):
        self.work_item_id = work_item_id
        super().__init__(f"Work item with id {work_item_id} not found")


class EmployeeHasAssignedWorkItemsError(Exception):
    """Raised when attempting to delete an employee with assigned work items."""

    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(
            f"Cannot delete employee with id {employee_id} because they have assigned work items"
        )
        
class EmployeeService:
    """SQLAlchemy-backed CRUD service for employee records."""

    @staticmethod
    def list_employees(
        db: Session,
        search: Optional[str] = None,
        department: Optional[str] = None,
        work_mode: Optional[WorkMode] = None,             
        is_active: Optional[bool] = None,             
        limit: int = 10,              
        offset: int = 0 
    ) -> tuple[int, list[EmployeeModel]]:
        """Filter, search, and paginate employees in MySQL."""
    
        try:
            query = db.query(EmployeeModel)
            
            if search and search.strip():
                query = query.filter(
                    func.lower(EmployeeModel.name).contains(search.strip().lower())
                )
                
            if department and department.strip():
                query = query.filter(
                    func.lower(EmployeeModel.department) == department.strip().lower()
                )
                
            if work_mode:
                query = query.filter(EmployeeModel.work_mode == work_mode.value)
            
            if is_active is not None:
                query = query.filter(EmployeeModel.is_active == is_active)
            
            total = query.count()
            
            items = query.order_by(EmployeeModel.id.asc()).offset(offset).limit(limit).all()
            return total, items
            
        except Exception as error:
            raise RuntimeError(
                "Database operation failed. Please try again."
            ) from error

    @staticmethod
    def get_employee(db: Session, employee_id: int) -> EmployeeModel:
        """Fetch a single employee by ID from MySQL."""
        try:
            employee = db.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
        except Exception as error:
            raise RuntimeError(
                "Database operation failed. Please try again."
            ) from error
        if employee is None:
            raise EmployeeNotFoundError(employee_id)
        return employee

    @staticmethod
    def get_employee_by_email(
        db: Session, email: str, exclude_id: Optional[int] = None
    ) -> Optional[EmployeeModel]:
        """Check if an email already exists (case-insensitive exact match)."""
        query = db.query(EmployeeModel).filter(
            func.lower(EmployeeModel.email) == email.strip().lower()
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
        except IntegrityError as error:
            db.rollback()
            raise DuplicateEmailError(payload.email) from error
        except Exception as error:
            db.rollback()
            raise RuntimeError(
                "Database operation failed. Please try again."
            ) from error

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
        except IntegrityError as error:
            db.rollback()
            raise DuplicateEmailError(payload.email) from error
        except Exception as error:
            db.rollback()
            raise RuntimeError(
                "Database operation failed. Please try again."
            ) from error

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> None:
        """Delete an employee record from MySQL."""
        employee = EmployeeService.get_employee(db, employee_id)

        # Check if employee has assigned work items before deleting
        has_work_items = (
            db.query(WorkItemModel)
            .filter(WorkItemModel.employee_id == employee_id)
            .first()
        )
        if has_work_items:
            raise EmployeeHasAssignedWorkItemsError(employee_id)

        try:
            db.delete(employee)
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise EmployeeHasAssignedWorkItemsError(employee_id) from error
        except Exception as error:
            db.rollback()
            raise RuntimeError(
                "Unable to delete the employee due to a database error. Please try again."
            ) from error
            
class WorkItemService:
    """SQLAlchemy-backed CRUD service for work items."""

    @staticmethod
    def create_work_item(db: Session, payload: WorkItemCreate) -> WorkItemModel:
        """Create and assign a work item to an employee."""
        # 1. Verify the assigned employee exists (raises 404 if not found)
        EmployeeService.get_employee(db, payload.employee_id)

        work_item = WorkItemModel(
            title=payload.title,
            description=payload.description,
            employee_id=payload.employee_id,
            status=payload.status.value,
            priority=payload.priority.value,
            due_date=payload.due_date,
        )
        try:
            db.add(work_item)
            db.commit()
            db.refresh(work_item)
            return work_item
        except Exception as error:
            db.rollback()
            raise RuntimeError("Database operation failed. Please try again.") from error

    @staticmethod
    def get_work_item(db: Session, work_item_id: int) -> WorkItemModel:
        """Fetch a single work item by ID from MySQL."""
        try:
            work_item = db.query(WorkItemModel).filter(WorkItemModel.id == work_item_id).first()
        except Exception as error:
            raise RuntimeError("Database operation failed. Please try again.") from error

        if work_item is None:
            raise WorkItemNotFoundError(work_item_id)
        return work_item

    @staticmethod
    def list_work_items(
        db: Session,
        search: Optional[str] = None,
        employee_id: Optional[int] = None,
        status: Optional[WorkItemStatus] = None,
        priority: Optional[WorkItemPriority] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[int, list[WorkItemModel]]:
        """Filter, search, and paginate work items in MySQL."""
        try:
            query = db.query(WorkItemModel)

            # Partial and case-insensitive search on title
            if search and search.strip():
                query = query.filter(
                    func.lower(WorkItemModel.title).contains(search.strip().lower())
                )

            # Filter by assigned employee
            if employee_id is not None:
                query = query.filter(WorkItemModel.employee_id == employee_id)

            # Filter by status
            if status:
                query = query.filter(WorkItemModel.status == status.value)

            # Filter by priority
            if priority:
                query = query.filter(WorkItemModel.priority == priority.value)

            total = query.count()
            # Order ascending by ID and apply pagination
            items = query.order_by(WorkItemModel.id.asc()).offset(offset).limit(limit).all()
            return total, items
        except Exception as error:
            raise RuntimeError("Database operation failed. Please try again.") from error

    @staticmethod
    def update_work_item(
        db: Session, work_item_id: int, payload: WorkItemUpdate
    ) -> WorkItemModel:
        """Update work item details or reassign to another employee."""
        work_item = WorkItemService.get_work_item(db, work_item_id)
        # Verify the new assigned employee exists (raises 404 if not found)
        EmployeeService.get_employee(db, payload.employee_id)

        work_item.title = payload.title
        work_item.description = payload.description
        work_item.employee_id = payload.employee_id
        work_item.status = payload.status.value
        work_item.priority = payload.priority.value
        work_item.due_date = payload.due_date

        try:
            db.commit()
            db.refresh(work_item)
            return work_item
        except Exception as error:
            db.rollback()
            raise RuntimeError("Database operation failed. Please try again.") from error

    @staticmethod
    def delete_work_item(db: Session, work_item_id: int) -> None:
        """Delete a work item from MySQL."""
        work_item = WorkItemService.get_work_item(db, work_item_id)
        try:
            db.delete(work_item)
            db.commit()
        except Exception as error:
            db.rollback()
            raise RuntimeError("Database operation failed. Please try again.") from error
            