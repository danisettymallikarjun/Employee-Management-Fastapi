from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import relationship  # pyright: ignore[reportMissingImports]
from app.database import Base

class EmployeeModel(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    department = Column(String(100), nullable=False)
    primary_skill = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    work_mode = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    work_items = relationship("WorkItemModel", back_populates="assigned_employee")
class WorkItemModel(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String(20), default="TODO", nullable=False)
    priority = Column(String(20), default="MEDIUM", nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    assigned_employee = relationship("EmployeeModel", back_populates="work_items")