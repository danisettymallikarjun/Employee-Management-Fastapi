# Employee Records API (Task 2 - MySQL & SQLAlchemy Integration)

A FastAPI backend for managing employee records, persisted in a MySQL database using SQLAlchemy ORM. Employee records remain permanently available even after restarting the application.

## Tech Stack

- **Python**: 3.12+
- **FastAPI**: Modern, high-performance web framework for building APIs
- **SQLAlchemy**: SQL toolkit and Object-Relational Mapper (ORM)
- **PyMySQL**: Pure-Python MySQL client driver
- **Cryptography**: Authentication backend for MySQL 8.0 `caching_sha2_password`
- **Pydantic v2**: Request validation, response serialization, and email format checking
- **Uvicorn**: Lightning-fast ASGI web server
- **Swagger UI**: Interactive API documentation generated at `/docs`

---

## Project Structure

```text
employee-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan setup & route endpoints
│   ├── database.py      # SQLAlchemy engine, session maker & get_db dependency
│   ├── models.py        # SQLAlchemy ORM model for MySQL 'employees' table
│   ├── schemas.py       # Pydantic validation schemas & field validators
│   └── services.py      # Database CRUD logic & transaction handling
├── screenshots/         # API execution screenshots
├── .env.example         # Environment template with placeholder values
├── .gitignore           # Git ignore file (excludes .env and virtual environments)
├── requirements.txt     # Project dependencies
└── README.md            # Setup, execution & architecture documentation
```

---

## Database Setup & Configuration

### 1. Create MySQL Database
Ensure MySQL Server is running, then open your MySQL client (e.g., MySQL Workbench, Command Line Client) and execute:

```sql
CREATE DATABASE IF NOT EXISTS employee_db;
```

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure your MySQL connection details:

```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=employee_db
```

> **Security Note:** The `.env` file is excluded from Git tracking via `.gitignore` to prevent exposing database credentials.

---

## Installation & Execution

### 1. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python -m uvicorn app.main:app --reload
```
*(Or via uv: `uv run python -m uvicorn app.main:app --reload`)*

On startup, SQLAlchemy automatically creates the `employees` table in your MySQL database via FastAPI's lifespan event.

### 4. Interactive Swagger Documentation
Open your browser and navigate to:
* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| **GET** | `/health` | Application liveness check | `200 OK` |
| **POST** | `/employees` | Create a new employee record | `201 Created`, `409 Conflict`, `422 Unprocessable` |
| **GET** | `/employees` | List all employee records | `200 OK` |
| **GET** | `/employees/{id}` | Get employee by integer ID | `200 OK`, `404 Not Found`, `422 Unprocessable` |
| **PUT** | `/employees/{id}` | Update employee record (full replace) | `200 OK`, `404 Not Found`, `409 Conflict`, `422 Unprocessable` |
| **DELETE** | `/employees/{id}` | Delete employee record | `204 No Content`, `404 Not Found`, `422 Unprocessable` |

---

## Data Model & Constraints

### Employee Fields
* `id` (int): Primary key, auto-incremented by MySQL.
* `name` (string): Full name (required, non-empty, non-whitespace).
* `email` (string): Unique email address (case-insensitive check + database-level unique index).
* `department` (string): Department name (required).
* `primary_skill` (string): Core technical or functional skill (required).
* `location` (string): Office or base location (required).
* `work_mode` (string): Enum restricted to `WFH` or `WFO`.
* `is_active` (bool): Defaults to `true` both in schema and database column.
* `created_at` (datetime): UTC timestamp generated at record creation; preserved during updates.

### Validation & Error Handling
* **Whitespace Validation**: Pydantic `@field_validator` rejects empty or whitespace-only inputs.
* **Case-Insensitive Email Uniqueness**: Enforced both via SQLAlchemy query (`func.lower(email)`) and MySQL table constraint.
* **Database Session Safety**: Sessions are injected using FastAPI's `Depends(get_db)` generator with `try ... finally: db.close()`, guaranteeing sessions are closed after every request.
* **Transaction Rollback**: If a database error occurs, `db.rollback()` is executed immediately to maintain database integrity and prevent session poisoning.

---

## Restart & Persistence Verification

To verify that data persists across application restarts:
1. Start the server: `python -m uvicorn app.main:app --reload`
2. Create an employee via `POST /employees` in Swagger UI (e.g. ID `1`).
3. Terminate the server (`Ctrl + C`).
4. Start the server again: `python -m uvicorn app.main:app --reload`
5. Call `GET /employees/1` in Swagger UI. The record is retrieved from MySQL with the original ID and `created_at` intact.

---

## Notes

### What I Learned
* How to use SQLAlchemy ORM with MySQL to replace in-memory data structures with durable relational storage.
* The difference between Pydantic validation schemas (`schemas.py`) and SQLAlchemy ORM models (`models.py`), and configuring `from_attributes = True` for smooth object serialization.
* Managing database connection lifecycles via FastAPI dependency injection (`get_db`) to guarantee session closure and prevent connection pool exhaustion.
* Ensuring transaction safety by handling database integrity errors with `db.rollback()` to prevent corrupted transaction states.

### Difficulties Faced
* Handling Windows security restrictions with standalone Python environments and ensuring proper MySQL driver support using `pymysql` and `cryptography`.
* Enforcing case-insensitive email uniqueness consistently across both application logic and database constraints during create and update operations.
* Ensuring `created_at` timestamps remain unchanged during `PUT` updates while updating all other editable fields.

### Assumptions Made
* `PUT /employees/{id}` executes a full replace of all editable fields; `created_at` and `id` remain untouched.
* Email comparison is strictly case-insensitive (`User@Example.com` and `user@example.com` are identical).
* Auto-increment IDs generated by MySQL are never reused after record deletion.
