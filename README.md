# TaskFlow

Task management REST API — Zomato backend take-home.

## 1. Overview

TaskFlow lets users register, log in, create projects, add tasks to projects, and assign tasks to each other. Core flows: auth, project CRUD, task CRUD with filters, and a stats endpoint for task counts.

## Features

- JWT Authentication
- Project CRUD
- Task CRUD
- Filtering & pagination
- Project stats endpoint
- Dockerized setup

**Stack I used:**

- Python 3.12 + FastAPI — I work in Python day to day so I went with this rather than Go. FastAPI handles async well and gives you free Swagger docs which made testing easier during development.
- PostgreSQL 16
- dbmate for migrations — simple, just plain SQL files, no magic
- bcrypt + JWT for auth
- Docker + docker-compose for the full setup

---

## 2. Architecture Decisions

**Why Python and not Go**
The spec said Go is preferred but allows other languages. I'm more comfortable in Python and figured I'd produce better quality code in less time using what I know. Go would give a smaller binary and better raw performance, but for a take-home at this scale that's not the real concern — correctness and structure matter more.

**Raw SQL over SQLAlchemy**
I initially thought of using SQLAlchemy because I've used it before, but switched to raw SQL with asyncpg pretty early. The main reason: migrations stay exactly as written, nothing gets auto-generated behind the scenes. When I looked at the schema requirements, it was clear enough that an ORM would've added complexity without much benefit here. The downside is you end up writing more boilerplate for mapping rows to objects.

**Router → Service → DB layers**
Routers only handle HTTP stuff (parsing request, returning response). Services hold the business logic — permission checks, validation that goes beyond Pydantic. DB access happens inside services through an injected connection. I kept it this way so if you wanted to test a service function, you just pass in a mock connection — you don't need to spin up a full HTTP server. Helped with writing the tests too.

**dbmate for migrations**
I looked at a few options. Went with dbmate because it's just a binary that runs numbered SQL files — no config, no ORM integration, no surprises. Both up and down migrations are in the same file. The migrate service in docker-compose runs it before the API starts so there's nothing manual to do.

**What I skipped and why**

- No refresh tokens. 24h JWT is fine for a take-home. In production I'd do short-lived access + refresh cookie.
- No `created_by` on tasks. The spec only mentions project owner for deletions so I didn't add it. Would be a quick migration to add though.
- No rate limiting on auth endpoints. Would add slowapi middleware on `/auth/login` if this were going to production.

---

## 3. Running Locally

Only Docker is needed — nothing else.

```bash
git clone https://github.com/your-name/taskflow
cd taskflow
cp .env.example .env
docker compose up
```

This runs in order: Postgres → migrations → seed data → API server. Should be ready in about 30 seconds.

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 4. Quick Flow

1. Register a user
2. Login to get JWT token
3. Click "Authorize" in Swagger and paste token
4. Create a project
5. Create tasks inside project
6. Update task status
7. View stats

## 5. Testing

Tested using Swagger UI at http://localhost:8000/docs

## 6. Running Migrations

Migrations run automatically on `docker compose up`. If you want to run them manually:

```bash
# run all pending
docker compose run --rm migrate up

# roll back one
docker compose run --rm migrate down
```

Migration files are at `backend/app/db/migrations/` — plain SQL, numbered, with up and down in each file.

---

## 7. Test Credentials

Seed data is loaded automatically on startup.

```
Email:    test@example.com
Password: password123
```

There's also 1 project and 3 tasks with different statuses so you can test the filters right away.

---

## 8. API Reference

All endpoints except `/auth/register` and `/auth/login` need: `Authorization: Bearer <token>`

Errors always come back as:

```json
{ "error": "validation failed", "fields": { "email": "already in use" } }
```

`422` validation · `401` unauthenticated · `403` forbidden · `404` not found

---

### Auth

**POST /auth/register**

```json
// request
{ "name": "Jane", "email": "jane@example.com", "password": "secret123" }

// 201 response
{ "token": "...", "user": { "id": "uuid", "name": "Jane", "email": "jane@example.com", "created_at": "..." } }
```

**POST /auth/login**

```json
// request
{ "email": "jane@example.com", "password": "secret123" }

// 200 response
{ "token": "...", "user": { ... } }
```

---

### Projects

| Method | Endpoint            | Notes                                   |
| ------ | ------------------- | --------------------------------------- |
| GET    | /projects           | projects you own or have tasks in       |
| POST   | /projects           | `{"name": "...", "description": "..."}` |
| GET    | /projects/:id       | project + its tasks                     |
| PATCH  | /projects/:id       | owner only                              |
| DELETE | /projects/:id       | owner only, cascades to tasks           |
| GET    | /projects/:id/stats | task counts by status + assignee        |

**Stats response:**

```json
{
  "by_status": { "todo": 1, "in_progress": 1, "done": 1 },
  "by_assignee": { "Jane": 2, "unassigned": 1 }
}
```

---

### Tasks

| Method | Endpoint            | Notes                                                  |
| ------ | ------------------- | ------------------------------------------------------ |
| GET    | /projects/:id/tasks | supports `?status=`, `?assignee=`, `?page=`, `?limit=` |
| POST   | /projects/:id/tasks | create a task                                          |
| PATCH  | /tasks/:id          | update any fields                                      |
| DELETE | /tasks/:id          | project owner only                                     |

---

## 9. What I'd Do With More Time

Honest list of what I know could be better:

**Shortcuts I took:**

- `updated_at` is handled by a Postgres trigger rather than in application code. Easier to set up, but it means tests can't easily control the timestamp value.
- Pagination is offset-based (`?page=&limit=`). Gets slow on large tables — cursor-based would be better but takes more time to implement correctly.
- Tests cover auth and tasks but I didn't get to writing project-level permission boundary tests (e.g. what happens when a non-owner tries to delete someone else's project). The happy paths are covered but edge cases on permissions need more coverage.
- I prioritised getting everything working correctly over deep optimisation. Some parts like the stats query could be made more efficient.

**Things I'd add:**

- Refresh tokens with short-lived access (15min) + httpOnly refresh cookie
- Rate limiting on the auth endpoints
- `created_by` on tasks so deletion can check creator OR owner
- Request ID middleware for tracing across logs
- Cursor-based pagination for the list endpoints
- More specific error codes (like `EMAIL_TAKEN`) alongside the human-readable message so frontends can handle errors programmatically
