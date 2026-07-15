# TaskFlow API

A production-style Task & Project Management REST API — built to demonstrate a real-world Django backend stack: JWT auth, async processing, containerization, and CI.

## Tech Stack
- Django + Django REST Framework
- JWT Authentication (SimpleJWT)
- PostgreSQL (Docker) / SQLite (local dev)
- Redis + Celery for async task reminders
- drf-yasg for Swagger/ReDoc API docs
- pytest + pytest-django for test coverage
- Docker + docker-compose
- GitHub Actions CI

## Features
- User registration & JWT login/refresh
- Project CRUD, scoped per user
- Task CRUD with status, priority, and due dates
- Async email reminders for due/overdue tasks via Celery
- Interactive API docs at /swagger/ and /redoc/
- Full test suite with 93% coverage
- One-command local environment via Docker Compose

## Quick Start (Docker)
```bash
cp .env.example .env
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```
API available at http://localhost:8000/, docs at http://localhost:8000/swagger/

## Quick Start (local, no Docker)
```bash
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Running Tests
```bash
pytest -v --cov=accounts --cov=projects --cov=tasks
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | /api/auth/register/ | Register new user |
| POST | /api/auth/login/ | Obtain JWT tokens |
| POST | /api/auth/token/refresh/ | Refresh access token |
| GET/POST | /api/projects/ | List / create projects |
| GET/PUT/DELETE | /api/projects/{id}/ | Retrieve / update / delete project |
| GET/POST | /api/tasks/ | List / create tasks (filter by status, priority, project) |
| GET/PUT/DELETE | /api/tasks/{id}/ | Retrieve / update / delete task |

## License
MIT
