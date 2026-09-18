# Swagger UI Screenshots & Evidence

This directory contains screenshots validating all API endpoints, error handling, and database persistence.

### 1. Core Endpoints & CRUD Operations
- **Health Check**: `GET /health` returning `200 OK`
- **Create Employee**: `POST /employees` returning `201 Created` with auto-generated ID 
- **List All Employees**: `GET /employees` returning `200 OK` with database records
- **Get Employee by ID**: `GET /employees/{id}` returning `200 OK`
- **Update Employee**: `PUT /employees/{id}` returning `200 OK` 
- **Delete Employee**: `DELETE /employees/{id}` returning `204 No Content`

### 2. Validation & Error Handling
- **Duplicate Email Validation**: Attempting to register an existing email returns `409 Conflict` (case-insensitive)
- **Employee Not Found**: Requesting a non-existent employee ID returns `404 Not Found`

### 3. Task 2 Persistence Evidence
- **Persistence After Restart**: Demonstrates creating an employee, stopping the server (`Ctrl + C`), restarting Uvicorn, and retrieving that same employee record via `GET /employees/{id}`.