# IS601 Final Project — BREAD Calculations API

This project demonstrates a full-stack implementation of BREAD (Browse, Read, Edit, Add, Delete) endpoints for a user-owned calculations resource, built with FastAPI, PostgreSQL, JWT authentication, and a browser-based dashboard. Three independent features extend the base application, each developed on its own branch with full backend, frontend, and test coverage.

## Quick Links

- [Docker Hub](https://hub.docker.com/r/ga424/is601_assignment14)
- [OpenAPI Docs](http://127.0.0.1:8013/docs) *(local)*
- [Architecture diagrams](docs/C4_ARCHITECTURE.md)
- [Helper script](start.sh)

---

## Features

### 1. Additional Calculation Types (`feature/additional-calculations`)

Adds three new operations beyond the base four (addition, subtraction, multiplication, division):

| Operation | Description | Example |
|-----------|-------------|---------|
| Exponentiation | Left-to-right `a ** b` | `2, 3` → `8` |
| Modulus | `a % b` (rejects divisor zero) | `10, 3` → `1` |
| Average | Mean of all inputs | `1, 2, 3` → `2` |

The dashboard dropdown is updated and the schema validates modulus-by-zero at the Pydantic layer.

### 2. User Profile & Password Change (`feature/user-profile`)

Lets authenticated users view and update their account credentials via `/profile`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/profile/me` | Return current user's profile |
| `PATCH` | `/profile/email` | Update email address |
| `PATCH` | `/profile/password` | Change password (verifies current password first) |

A dedicated profile page (`/profile`) provides forms for both actions, accessible via a "Profile" link in the dashboard header.

### 3. Report / History (`feature/reports-history`)

Provides per-user usage statistics via `GET /reports`:

| Field | Description |
|-------|-------------|
| `total_calculations` | Total number of calculations run |
| `by_type` | Count per calculation type |
| `average_result` | Mean of all stored results |
| `most_used_type` | The operation used most |

A "Usage Report" panel on the dashboard loads automatically and refreshes after every create or delete.

---

## BREAD Endpoints

All calculation endpoints require a valid JWT (`Authorization: Bearer <token>`). Each user can only access their own calculations.

| Operation | Method | Path | Description |
|-----------|--------|------|-------------|
| Browse | `GET` | `/calculations` | List all calculations for the logged-in user |
| Read | `GET` | `/calculations/{id}` | Retrieve a single calculation by ID |
| Edit | `PUT` | `/calculations/{id}` | Update operation type, inputs, and result |
| Add | `POST` | `/calculations` | Create a new calculation |
| Delete | `DELETE` | `/calculations/{id}` | Remove a calculation |

**Authentication endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/register` | Create a new user account, returns JWT |
| `POST` | `/login` | Authenticate and receive a JWT |

**Profile endpoints** *(feature/user-profile)*:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/profile/me` | Get current user's profile |
| `PATCH` | `/profile/email` | Update email |
| `PATCH` | `/profile/password` | Change password |

**Report endpoint** *(feature/reports-history)*:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reports` | Return usage statistics for the current user |

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

---

## Run Locally

Start PostgreSQL with Docker:

```bash
docker compose up -d db
```

Run the app:

```bash
uvicorn app.main:app --reload --port 8013
```

Pages:

- `http://127.0.0.1:8013/register`
- `http://127.0.0.1:8013/login`
- `http://127.0.0.1:8013/dashboard`
- `http://127.0.0.1:8013/profile` *(feature/user-profile)*
- `http://127.0.0.1:8013/docs`

---

## Running Tests

### All unit + API tests (no app required)

```bash
python3 -m pytest -q -m "not e2e"
```

### Validating each feature independently

Switch to the feature branch, then run the command for that feature.

**Additional Calculation Types**

```bash
git checkout feature/additional-calculations
./start.sh test-unit-calcs      # unit + API tests for new operations
./start.sh up                   # start the full stack
./start.sh test-e2e-calcs       # E2E tests for new operations
```

**User Profile & Password Change**

```bash
git checkout feature/user-profile
./start.sh test-unit-profile    # unit + API tests for profile endpoints
./start.sh up
./start.sh test-e2e-profile     # E2E tests: view, update email, change password
```

**Report / History**

```bash
git checkout feature/reports-history
./start.sh test-unit-reports    # unit + API tests for the /reports endpoint
./start.sh up
./start.sh test-e2e-reports     # E2E tests: panel visibility, counts, refresh
```

### Run all E2E tests (full stack must be running)

```bash
./start.sh up
python3 -m playwright install chromium
python3 -m pytest -q -m e2e
```

### Specific test files

```bash
# Unit / model tests
python3 -m pytest tests/test_models.py

# API integration tests
python3 -m pytest tests/test_api.py

# DB integration tests (needs live PostgreSQL)
python3 -m pytest tests/test_integration_db.py

# E2E by feature
python3 -m pytest tests/test_e2e_calculations.py   # feature/additional-calculations
python3 -m pytest tests/test_e2e_profile.py        # feature/user-profile
python3 -m pytest tests/test_e2e_reports.py        # feature/reports-history
```

---

## Full Stack with Docker

```bash
./start.sh up       # start db + app
./start.sh test     # run all non-E2E tests in a container
./start.sh down     # stop everything
./start.sh clean    # remove containers and volumes
```

Run a security scan:

```bash
./start.sh scan
```

Build and run the image directly:

```bash
docker build -t ga424/is601_assignment14:latest .
docker run --rm -p 8013:8013 ga424/is601_assignment14:latest
```

---

## Example Requests

Register and login:

```bash
curl -X POST http://127.0.0.1:8013/register \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"strongpassword123"}'

curl -X POST http://127.0.0.1:8013/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"strongpassword123"}'
```

Create calculations (set `TOKEN` to the `access_token` from login):

```bash
curl -X POST http://127.0.0.1:8013/calculations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"exponentiation","inputs":[2,10]}'

curl -X POST http://127.0.0.1:8013/calculations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"average","inputs":[10,20,30,40]}'
```

Fetch usage report:

```bash
curl http://127.0.0.1:8013/reports \
  -H "Authorization: Bearer $TOKEN"
```

Update profile:

```bash
curl -X PATCH http://127.0.0.1:8013/profile/email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"newemail@example.com"}'

curl -X PATCH http://127.0.0.1:8013/profile/password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"strongpassword123","new_password":"newsecurepass456"}'
```

---

## CI/CD

- **CI workflow** (`.github/workflows/ci.yml`): starts PostgreSQL and the app, runs all pytest unit and Playwright E2E tests.
- **Docker publish** (`.github/workflows/docker-publish.yml`): repeats the test flow, then builds and pushes the Docker image to Docker Hub on tags (`v*`) or manual dispatch.
- **Security scan** (`.github/workflows/security-scan.yml`): runs Trivy filesystem and image scans.

Required repository secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

---

## Notes

- The model stores physical `a` and `b` columns for the first two operands and keeps `inputs[]` for the full request payload.
- The documentation in `docs/` includes the C4 architecture view and a navigation index.
- Docker Hub repository: [hub.docker.com/r/ga424/is601_assignment14](https://hub.docker.com/r/ga424/is601_assignment14)
