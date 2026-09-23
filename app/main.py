"""
FastAPI application entrypoint backed by MySQL and SQLAlchemy.

Run with:
        uv run python -m uvicorn app.main:app --reload
        
Then open http://127.0.0.1:8000/docs for Swagger UI.
"""

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status  # type: ignore[reportMissingImports]
from fastapi.exceptions import RequestValidationError  # type: ignore[reportMissingImports]
from fastapi.responses import JSONResponse  # type: ignore[reportMissingImports]
from app.database import Base, engine, get_db
from app.schemas import ( Employee, EmployeeCreate, EmployeeUpdate, ErrorResponse , EmployeeListResponse , WorkMode, )
from app.services import (
    DuplicateEmailError,
    EmployeeNotFoundError,
    EmployeeService,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically creates the 'employees' table in MySQL if it doesn't exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Employee Records API",
    description="FastAPI backend backed by MySQL and SQLAlchemy.",
    version="2.0.0",
    lifespan=lifespan,
)

EmployeeIdPath = Path(..., gt=0, description="Positive integer employee id")

@app.get("/")
def root():
    return {"message": "Employee API is running"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error["loc"] if part != "body")
        messages.append(f"{loc}: {error['msg']}" if loc else error["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(messages)},
    )


@app.get("/health", tags=["Health"], summary="Health check")
def health_check() -> dict:
    return {"status": "ok"}


@app.post(
    "/employees",
    response_model=Employee,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"],
    summary="Create an employee",
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def create_employee(
    payload: EmployeeCreate,
    db: Any = Depends(get_db),
) -> Employee:
    try:
        return EmployeeService.create_employee(db, payload)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
            
@app.get(
    "/employees",
    response_model=EmployeeListResponse,
    tags=["Employees"],
    summary="List all employees With Search,Filter and Pagination",
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
        },
)
def list_employees(
        search: Optional[str] = Query(
        default=None, description="Search employee name (partial match, case-insensitive)"
    ),
    department: Optional[str] = Query(
        default=None, description="Filter by department"
    ),
    work_mode: Optional[WorkMode] = Query(
        default=None, description="Filter by WFH or WFO"
    ),
    is_active: Optional[bool] = Query(
        default=None, description="Filter by active status (true/false)"
    ),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of records to return (1-100)"
    ),
    offset: int = Query(
        default=0, ge=0, description="Number of records to skip"
    ),
    db: Any = Depends(get_db),
) -> dict:
    try:
        total, items = EmployeeService.list_employees(
            db=db,
            search=search,
            department=department,
            work_mode=work_mode,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@app.get(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Get an employee by ID",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def get_employee(
    employee_id: int = EmployeeIdPath,
    db: Any = Depends(get_db),
) -> Employee:
    try:
        return EmployeeService.get_employee(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@app.put(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Update an employee",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def update_employee(
    payload: EmployeeUpdate,
    employee_id: int = EmployeeIdPath,
    db: Any = Depends(get_db),
) -> Employee:
    try:
        return EmployeeService.update_employee(db, employee_id, payload)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    
@app.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Employees"],
    summary="Delete an employee",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def delete_employee(
    employee_id: int = EmployeeIdPath,
    db: Any = Depends(get_db),
) -> None:
    try:
        EmployeeService.delete_employee(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
   