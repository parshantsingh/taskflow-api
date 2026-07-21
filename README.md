# TaskFlow API

A production-style Task & Project Management REST API — built to demonstrate a real-world Django backend stack spanning authentication, async processing, real-time updates, AI/RAG integration, webhooks, and 12-factor deployment practices.

## Tech Stack

- **Backend**: Django, Django REST Framework
- **Auth**: JWT (SimpleJWT), rate limiting, account lockout, password reset
- **Database**: PostgreSQL (Docker) / SQLite (local dev)
- **Async**: Celery, Redis, Celery Beat scheduling
- **Real-time**: Django Channels (WebSockets)
- **AI/ML**: Claude API (generation, summarization, classification) + Voyage AI embeddings for semantic search RAG
- **Docs**: drf-yasg (Swagger/ReDoc)
- **Testing**: pytest, pytest-django, 51+ tests, mocked external APIs
- **Infra**: Docker, docker-compose, GitHub Actions CI, split settings (base/dev/prod), structured logging, health checks

## Features

- **Auth & security**: JWT login/refresh, registration, password reset, rate limiting, brute-force lockout
- **Projects & teams**: role-based membership (owner/admin/member), invites
- **Tasks**: CRUD, subtasks, task dependencies with cycle prevention, full-text search, filtering, ordering
- **Collaboration**: comments, activity/audit log, in-app notifications
- **Time tracking**: start/stop timers, estimated vs. actual hours
- **Files**: attachments, CSV export
- **AI**: auto-generated task descriptions, priority suggestions, project summaries, natural-language project Q&A (RAG)
- **Real-time**: live activity feed via WebSockets
- **Automation**: scheduled overdue-task checks, webhooks with HMAC-signed payloads and retry logic
- **Analytics**: cached project stats, cross-project dashboard overview
- **Ops**: health checks, structured logging, consistent error responses, admin panel with search/filters

## Quick Start (Docker)

```bash
cp .env.example .env
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_demo_data
docker-compose exec web python manage.py createsuperuser
```
API available at `http://localhost:8000/`, docs at `http://localhost:8000/swagger/`.

## Quick Start (local, no Docker)

```bash
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```
Demo login: `alice` / `demopass123` (also `bob`, `carol`).

## Running Tests

```bash
pytest -v --cov=accounts --cov=projects --cov=tasks --cov=notifications --cov=webhooks
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Obtain JWT tokens (rate-limited, lockout after 5 failed attempts) |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| POST | `/api/auth/password-reset/` | Request password reset email |
| POST | `/api/auth/password-reset-confirm/` | Confirm password reset with token |

### Projects
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET/POST | `/api/projects/` | List / create projects |
| GET/PUT/DELETE | `/api/projects/{id}/` | Retrieve / update / delete project |
| GET/POST | `/api/projects/{id}/members/` | List / invite project members |
| DELETE | `/api/projects/{id}/members/{user_id}/` | Remove a member |
| GET | `/api/projects/{id}/stats/` | Cached task stats by status/priority |
| GET | `/api/projects/{id}/ai-summary/` | AI-generated standup summary |
| POST | `/api/projects/{id}/ask/` | Ask a natural-language question about the project (RAG) |
| GET | `/api/projects/analytics/overview/` | Cross-project analytics dashboard |

### Tasks
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET/POST | `/api/tasks/` | List / create tasks (filter: `status`, `priority`, `project`, `search`, `due_date_after/before`; order: `ordering`) |
| GET/PUT/DELETE | `/api/tasks/{id}/` | Retrieve / update / delete task |
| POST | `/api/tasks/{id}/subtasks/` | Create a subtask |
| POST/DELETE | `/api/tasks/{id}/block-by/{blocker_id}/` | Add/remove a blocking dependency |
| GET/POST | `/api/tasks/{id}/comments/` | List / add comments |
| GET | `/api/tasks/{id}/activity/` | Task activity/audit log |
| GET/POST | `/api/tasks/{id}/attachments/` | List / upload attachments |
| DELETE | `/api/tasks/{id}/attachments/{attachment_id}/` | Delete an attachment |
| POST | `/api/tasks/{id}/time/start` | Start a timer |
| POST | `/api/tasks/{id}/time/stop` | Stop the running timer |
| GET | `/api/tasks/{id}/time` | List time entries |
| GET | `/api/tasks/export-csv/` | Export filtered tasks as CSV |
| POST | `/api/tasks/ai-generate-description/` | AI-generated task description |
| POST | `/api/tasks/ai-suggest-priority/` | AI-suggested priority with reasoning |

### Notifications
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/api/notifications/` | List notifications |
| GET | `/api/notifications/unread-count/` | Unread count |
| POST | `/api/notifications/{id}/mark-read/` | Mark one as read |
| POST | `/api/notifications/mark-all-read/` | Mark all as read |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET/POST | `/api/webhooks/` | List / register a webhook (owner/admin only) |
| GET | `/api/webhooks/{id}/deliveries/` | Delivery history for a webhook |

### Ops
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/health/` | Health check (DB + cache) |
| GET | `/swagger/`, `/redoc/` | Interactive API docs |

## License
MIT
