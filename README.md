# Task Manager API

A backend system for managing projects and tracking tasks with workflow validation, role-based access control, Redis caching, and structured logging — built with FastAPI and SQLite.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Entities & Data Models](#entities--data-models)
- [Roles & Permissions](#roles--permissions)
- [Task Status Lifecycle](#task-status-lifecycle)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication)
  - [Users](#users)
  - [Projects](#projects)
  - [Tasks](#tasks)
  - [System](#system)
- [Caching Strategy](#caching-strategy)
- [Logging](#logging)
- [Metrics & Monitoring](#metrics--monitoring)
- [Getting Started](#getting-started)
  - [Running Locally](#running-locally)
  - [Running with Docker](#running-with-docker)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [Design Decisions](#design-decisions)

---

## Overview

Task Manager is a RESTful API backend that enables organizations to manage projects and track task progress across teams. It enforces a strict task status lifecycle (`To Do → In Progress → Done`), role-based access control with three distinct roles, and optional Redis caching to reduce database load on frequently read endpoints.

### Key Features

- JWT-based authentication with role-aware authorization
- Full project and task CRUD with ownership rules
- Enforced one-directional task status transitions
- Filterable task queries (by status, priority, and assignee)
- Redis caching with automatic invalidation on writes
- Structured application logging (per-request and per-event)
- In-memory API metrics (request count, error rate, response time)
- Health check and admin dashboard endpoints
- Docker and Docker Compose support

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Auth | JWT (JSON Web Tokens) + bcrypt |
| Caching | Redis (optional, gracefully degraded) |
| Validation | Pydantic v2 |
| Testing | pytest + FastAPI TestClient |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
task_manager/
├── app/
│   ├── main.py                  # App entry point, middleware, global routes
│   ├── database.py              # SQLAlchemy engine and session setup
│   ├── models/
│   │   ├── user.py              # User ORM model
│   │   ├── project.py           # Project ORM model
│   │   └── task.py              # Task ORM model
│   ├── schemas/
│   │   ├── user.py              # Pydantic schemas for users
│   │   ├── project.py           # Pydantic schemas for projects
│   │   └── task.py              # Pydantic schemas for tasks
│   ├── routes/
│   │   ├── auth.py              # Register and login endpoints
│   │   ├── users.py             # User management endpoints
│   │   ├── projects.py          # Project CRUD endpoints
│   │   └── tasks.py             # Task CRUD + filtering endpoints
│   ├── dependencies/
│   │   ├── auth.py              # JWT extraction and user resolution
│   │   └── roles.py             # Role enforcement helper
│   └── core/
│       ├── security.py          # Password hashing and JWT utilities
│       ├── logging_config.py    # Logger configuration
│       ├── metrics.py           # In-memory metrics collector
│       └── redis_client.py      # Redis connection setup
├── tests/
│   ├── test_auth.py
│   ├── test_projects.py
│   └── test_tasks.py
├── frontend/                    # Simple HTML/JS frontend (optional)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── task_manager.db              # SQLite database file (auto-created)
```

---

## Entities & Data Models

### User

| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key, auto-increment |
| `username` | String | Unique, indexed |
| `email` | String | Unique, indexed |
| `password` | String | Bcrypt hashed |
| `role` | String | `admin` / `manager` / `employee` |

New users who self-register via `/auth/register` are always assigned the `employee` role. Admins can promote users through the users endpoint.

---

### Project

| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key, auto-increment |
| `name` | String | — |
| `description` | String | — |
| `created_by` | Integer | Foreign key → `users.id` |

---

### Task

| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key, auto-increment |
| `title` | String | — |
| `description` | String | — |
| `status` | String | Default: `To Do` |
| `priority` | String | e.g. `Low`, `Medium`, `High` |
| `project_id` | Integer | Foreign key → `projects.id` |
| `assigned_to` | Integer | Foreign key → `users.id` |

---

## Roles & Permissions

| Action | Admin | Manager | Employee |
|---|:---:|:---:|:---:|
| Register / Login | ✅ | ✅ | ✅ |
| View own profile (`/me`) | ✅ | ✅ | ✅ |
| List all users | ✅ | ❌ | ❌ |
| Create / update / delete users | ✅ | ❌ | ❌ |
| Create projects | ✅ | ❌ | ❌ |
| View all projects | ✅ | ✅ | ✅ |
| Update / delete projects | ✅ | ❌ | ❌ |
| Create tasks | ✅ | ✅ | ❌ |
| View all tasks | ✅ | ✅ | ❌ |
| View own assigned tasks only | — | — | ✅ |
| Update any task | ✅ | ✅ | ❌ |
| Update own assigned task | ✅ | ✅ | ✅ |
| Delete tasks | ✅ | ❌ | ❌ |
| Access `/dashboard` | ✅ | ❌ | ❌ |

Employees are fully scoped to their own assignments — they cannot see, filter, or update tasks that belong to other users.

---

## Task Status Lifecycle

Tasks follow a strict, one-directional status workflow. Attempting to skip or reverse a step returns a `400 Bad Request`.

```
To Do  ──►  In Progress  ──►  Done
```

| Current Status | Allowed Next Status |
|---|---|
| `To Do` | `In Progress` |
| `In Progress` | `Done` |
| `Done` | *(terminal — no further transitions)* |

**Example — valid transition:**
```json
PUT /tasks/5
{ "status": "In Progress" }
```

**Example — invalid transition (task is already Done):**
```json
PUT /tasks/5
{ "status": "To Do" }
// 400: Cannot transition from 'Done' to 'To Do'
```

---

## API Endpoints

All endpoints except `/auth/register` and `/auth/login` require a valid JWT in the `Authorization: Bearer <token>` header.

---

### Authentication

#### `POST /auth/register`

Register a new user. Automatically assigned the `employee` role.

**Request body:**
```json
{
  "username": "jane",
  "email": "jane@example.com",
  "password": "secret123"
}
```

**Response `201`:**
```json
{
  "id": 3,
  "username": "jane",
  "email": "jane@example.com",
  "role": "employee"
}
```

---

#### `POST /auth/login`

Authenticate and receive a JWT access token.

**Request body:**
```json
{
  "username": "jane",
  "password": "secret123"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "employee"
}
```

---

### Users

#### `GET /me`

Returns the currently authenticated user's profile.

---

#### `GET /users/`

List all users. **Admin only.**

---

#### `GET /users/{user_id}`

Get a specific user by ID. **Admin only.**

---

#### `POST /users/`

Create a user with an explicit role. **Admin only.**

**Request body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "pass",
  "role": "manager"
}
```

---

#### `PUT /users/{user_id}`

Update a user's information (username, email, password, role). **Admin only.**

---

#### `DELETE /users/{user_id}`

Delete a user. **Admin only.**

---

### Projects

#### `POST /projects/`

Create a new project. **Admin only.**

**Request body:**
```json
{
  "name": "Website Redesign",
  "description": "Full overhaul of the marketing site"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "name": "Website Redesign",
  "description": "Full overhaul of the marketing site",
  "created_by": 1
}
```

---

#### `GET /projects/`

List all projects. **All authenticated roles.**

Results are cached in Redis for 60 seconds and invalidated on any write.

---

#### `GET /projects/{project_id}`

Get a single project by ID. **All authenticated roles.**

---

#### `PUT /projects/{project_id}`

Update a project's name or description. **Admin only.**

---

#### `DELETE /projects/{project_id}`

Delete a project. **Admin only.**

---

### Tasks

#### `POST /tasks/`

Create a new task and assign it to a user. **Admin and Manager only.**

The referenced `project_id` and `assigned_to` user must both exist, or the request returns `400`.

**Request body:**
```json
{
  "title": "Design login page",
  "description": "Create Figma mockups",
  "priority": "High",
  "project_id": 1,
  "assigned_to": 3
}
```

---

#### `GET /tasks/`

List tasks with optional filters. Results are cached per unique filter combination and role.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by status: `To Do`, `In Progress`, `Done` |
| `priority` | string | Filter by priority: `Low`, `Medium`, `High` |
| `assigned_to` | integer | Filter by assigned user ID |

Employees automatically see only their own tasks regardless of filters. Attempting to filter by another user's ID returns `403`.

**Example:**
```
GET /tasks/?status=In Progress&priority=High
```

---

#### `GET /tasks/{task_id}`

Get a single task by ID. Employees can only access tasks assigned to them.

---

#### `PUT /tasks/{task_id}`

Update a task's title, description, priority, or status.

- Admins and Managers can update any task.
- Employees can only update tasks assigned to them.
- Status transitions are validated (see [Task Status Lifecycle](#task-status-lifecycle)).

**Request body (all fields optional):**
```json
{
  "status": "In Progress",
  "priority": "Medium"
}
```

---

#### `DELETE /tasks/{task_id}`

Permanently delete a task. **Admin only.**

---

### System

#### `GET /`

Health check — confirms the API is running.

#### `GET /health`

Deep health check — verifies database connectivity.

```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### `GET /metrics`

Returns aggregate API metrics (public).

```json
{
  "total_requests": 142,
  "total_errors": 3,
  "average_response_time": 0.0042
}
```

#### `GET /dashboard`

Extended metrics with recent request logs. **Admin only.**

```json
{
  "total_requests": 142,
  "total_errors": 3,
  "error_rate": 0.0211,
  "average_response_time": 0.0042,
  "recent_logs": [
    "GET /tasks/ 200",
    "POST /tasks/ 200",
    "PUT /tasks/5 400"
  ],
  "status": "running"
}
```

#### `GET /redis-test`

Validates that the Redis connection is working. Writes and reads a test key.

#### `GET /cache-benchmark`

Compares query execution time between the database and Redis cache for the projects list.

```json
{
  "db_query_time_seconds": 0.000812,
  "cache_query_time_seconds": 0.000044,
  "improvement": "94.58% faster"
}
```

---

## Caching Strategy

Redis is used as an optional read-through cache. If Redis is unavailable, all requests fall back to the database without any errors surfaced to the client.

| Cache Key Pattern | TTL | Invalidated On |
|---|---|---|
| `projects:all` | 60s | Any project create / update / delete |
| `tasks:<filters>:<role>:<user_id>` | 60s | Any task create / update / delete |
| `task:<task_id>:<role>:<user_id>` | 60s | That specific task update / delete |
| `users:all` | 60s | Any user create / update / delete |

Cache keys are scoped by role and user ID so employees only ever receive their own data from cache — there is no cross-user data leakage.

On any mutation, the API invalidates all related keys using Redis wildcard patterns (`tasks:*`, `task:{id}:*`) to ensure consistency.

---

## Logging

All significant events are logged using Python's standard `logging` module, configured in `app/core/logging_config.py`. Logs are written to `app.log` and streamed to stdout.

Log levels used throughout the application:

| Level | Usage |
|---|---|
| `DEBUG` | Incoming request details, filter parameters |
| `INFO` | Successful creates, updates, deletes, cache hits |
| `WARNING` | Unauthorized access attempts, invalid filter abuse |
| `ERROR` | Missing resources (project/user not found) |
| `CRITICAL` | Corrupt database state (unexpected status value) |

HTTP middleware logs every request with its method, path, status code, and processing time.

---

## Metrics & Monitoring

The API tracks lightweight in-memory metrics via `app/core/metrics.py`. Metrics are reset when the server restarts.

- **Total request count** — incremented on every HTTP request
- **Total error count** — incremented on any 5xx response
- **Total response time** — accumulated for average calculation
- **Recent logs** — rolling buffer of recent request log lines (for `/dashboard`)

These are exposed via `GET /metrics` (public) and `GET /dashboard` (admin only).

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip
- Redis (optional — the app runs fine without it)

---

### Running Locally

**1. Clone the repository and navigate into the project:**

```bash
git clone <repo-url>
cd task_manager
```

**2. Create and activate a virtual environment:**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Start the development server:**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive documentation is served automatically at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

**5. Create an admin user (first-time setup):**

Since `/auth/register` always creates `employee` accounts, the first admin must be created directly in the database, or by temporarily modifying the register route. Once an admin exists, they can create other admins and managers via `POST /users/`.

---

### Running with Docker

Docker Compose starts the API and Redis together.

```bash
docker compose up --build
```

The API is exposed on port `8000` and Redis on `6379`.

To run in detached mode:

```bash
docker compose up -d --build
```

To stop:

```bash
docker compose down
```

**Environment variables passed by Docker Compose:**

| Variable | Value |
|---|---|
| `DOCKER_ENV` | `true` |
| `SECRET_KEY` | `your-very-secret-key-here` |

Change `SECRET_KEY` before deploying to any non-local environment.

---

## Running Tests

Tests use `pytest` with FastAPI's built-in `TestClient`. They run against a real (test) database.

```bash
pytest tests/
```

To run a specific test file:

```bash
pytest tests/test_tasks.py -v
```

Test coverage includes:

- `test_auth.py` — Registration and login flows
- `test_projects.py` — Project creation, retrieval, permission enforcement
- `test_tasks.py` — Task creation, role restrictions, status transition validation, filtering

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Secret key used to sign JWTs | `your-very-secret-key-here` |
| `DOCKER_ENV` | When `true`, Redis connects to `redis` hostname (Docker network) | `false` |

The application reads these from the environment. In local development without Docker, set them in your shell or a `.env` file.

---

## Design Decisions

**SQLite for persistence** — SQLite requires no external service, making the project easy to run locally and in CI. For production use, the SQLAlchemy ORM makes it straightforward to switch to PostgreSQL or MySQL by changing the connection string in `database.py`.

**Redis as optional infrastructure** — Every Redis call is wrapped in a `try/except`. If Redis is not running, the application falls back to the database transparently. This prevents a caching layer outage from taking down the entire API.

**Role enforcement at the route level** — Roles are checked inline within each route handler using `require_role()` and `current_user.role` comparisons. This keeps authorization logic explicit and auditable without a separate middleware layer.

**Cache keys include role and user ID** — Scoping cache keys by the requesting user's role and ID prevents data from one user's cache entry from being returned to another user. This is especially important for employees, who should only ever see their own tasks.

**Status transitions are a server-side rule** — The valid transitions map lives in the update route rather than the database schema, making it easy to extend or reconfigure the workflow without a migration.

**Passwords are hashed with bcrypt** — The `security.py` module uses `passlib` with bcrypt for all password hashing and verification. Plaintext passwords are never stored.
