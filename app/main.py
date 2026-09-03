"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for Swagger UI.
"""

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import Employee, EmployeeCreate, EmployeeUpdate, ErrorResponse
from app.services import (
    DuplicateEmailError,
    EmployeeNotFoundError,
    employee_service,
)

app = FastAPI(
    title="Employee Records API",
    description=(
        "A simple FastAPI backend for managing employee records, backed by "
        "an in-memory Python list. Data resets on restart; no database in "
        "this stage of the project."
    ),
    version="1.0.0",
)

# A reusable path parameter with a strict validation rule: id must be a
# positive integer (gt=0), so 0 or negative ids are rejected with a 422
# before the route body even runs.
EmployeeIdPath = Path(..., gt=0, description="Positive integer employee id")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Return a clearer, consistent error body for validation failures
    (missing required fields, bad email format, invalid work_mode, invalid
    id, etc.) instead of FastAPI's default verbose structure.
    """
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
    """Simple liveness check used to confirm the application is running."""
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
def create_employee(payload: EmployeeCreate) -> Employee:
    try:
        return employee_service.create_employee(payload)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.get(
    "/employees",
    response_model=list[Employee],
    tags=["Employees"],
    summary="List all employees",
)
def list_employees() -> list[Employee]:
    return employee_service.list_employees()


@app.get(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Get an employee by ID",
    responses={404: {"model": ErrorResponse, "description": "Employee not found"}},
)
def get_employee(employee_id: int = EmployeeIdPath) -> Employee:
    try:
        return employee_service.get_employee(employee_id)
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
def update_employee(payload: EmployeeUpdate, employee_id: int = EmployeeIdPath) -> Employee:
    try:
        return employee_service.update_employee(employee_id, payload)
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
def delete_employee(employee_id: int = EmployeeIdPath) -> None:
    try:
        employee_service.delete_employee(employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
