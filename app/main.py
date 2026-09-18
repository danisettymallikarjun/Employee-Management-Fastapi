"""
FastAPI application entrypoint backed by MySQL and SQLAlchemy.

Run with:
        uv run python -m uvicorn app.main:app --reload
        
Then open http://127.0.0.1:8000/docs for Swagger UI.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Path, status  # type: ignore[reportMissingImports]
from fastapi.exceptions import RequestValidationError  # type: ignore[reportMissingImports]
from fastapi.responses import JSONResponse  # type: ignore[reportMissingImports]
from app.database import Base, engine, get_db
from app.schemas import Employee, EmployeeCreate, EmployeeUpdate, ErrorResponse
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


@app.get(
    "/employees",
    response_model=list[Employee],
    tags=["Employees"],
    summary="List all employees",
)
def list_employees(db: Any = Depends(get_db)) -> list[Employee]:
    return EmployeeService.list_employees(db)


@app.get(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Get an employee by ID",
    responses={404: {"model": ErrorResponse, "description": "Employee not found"}},
)
def get_employee(
    employee_id: int = EmployeeIdPath,
    db: Any = Depends(get_db),
) -> Employee:
    try:
        return EmployeeService.get_employee(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.put(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Update an employee",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
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


@app.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Employees"],
    summary="Delete an employee",
    responses={404: {"model": ErrorResponse, "description": "Employee not found"}},
)
def delete_employee(
    employee_id: int = EmployeeIdPath,
    db: Any = Depends(get_db),
) -> None:
    try:
        EmployeeService.delete_employee(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))