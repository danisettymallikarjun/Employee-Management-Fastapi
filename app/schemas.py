"""
Pydantic models (schemas) used for request validation and response
serialization.

Two "shapes" of employee model are defined:

- EmployeeCreate  -> what the client sends on POST /employees
- EmployeeUpdate  -> what the client sends on PUT /employees/{id}
- Employee        -> what the API returns (includes id, created_at, etc.)
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field , field_validator    # type: ignore[import-not-found]


class WorkMode(str, Enum):
    """Allowed values for work_mode. Using an Enum means FastAPI/Pydantic
    will automatically reject anything other than WFH or WFO with a 422."""

    WFH = "WFH"
    WFO = "WFO"


class EmployeeBase(BaseModel):
    """Fields shared between create and update requests."""

    name: str = Field(..., min_length=1, description="Full name of the employee")
    email: EmailStr = Field(..., description="Unique work email address")
    department: str = Field(..., min_length=1, description="Department the employee belongs to")
    primary_skill: str = Field(..., min_length=1, description="Primary technical/functional skill")
    location: str = Field(..., min_length=1, description="Work location / city")
    work_mode: WorkMode = Field(..., description="Either WFH or WFO")
    is_active: bool = Field(default=True, description="Whether the employee is currently active")


    @field_validator("name", "department", "primary_skill", "location", mode="before")
    @classmethod
    def check_not_empty_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or contain only whitespace.")
            return stripped
        return value

class EmployeeCreate(EmployeeBase):
    """Payload for POST /employees. id/created_at are server-generated."""
    pass

class EmployeeUpdate(EmployeeBase):
    """Payload for PUT /employees/{id}.

    This project uses PUT as a full replace (all fields required), which
    keeps validation rules simple and consistent with the create schema.
    """
    pass

class Employee(EmployeeBase):
    """Full employee record as returned by the API."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    """Generic error envelope used for documented error responses in Swagger."""

    detail: str

class EmployeeListResponse(BaseModel):
    """Envelope response for the paginated employee list."""
    total: int
    limit: int
    offset: int
    items: list[Employee]