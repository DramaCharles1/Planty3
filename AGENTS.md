# AGENTS.md

This file is for agentic coding tools working in this repo.

Repository: Dockerized Django + Postgres + MQTT (Mosquitto).

## Quick Orientation

- `docker-compose.yaml`: runs `mqtt`, `postgres`, `adminer`, `backend`, `mqtt_client`
- `.env`: dev defaults used by compose (DB/MQTT). Treat as non-secret in this repo.
- `backend/`: Django project
  - `backend/manage.py`
  - `backend/planty/`: settings/urls
  - `backend/motherplant/`: models + MQTT ingest management command + tests
- `mqtt/`: mosquitto config + topic/schema documentation + local MQTT test client

## Build / Run (Docker)

Prereqs: Docker + docker compose.

Start core dependencies:

- `docker compose up -d postgres mqtt`

Start Django dev server:

- `docker compose up -d backend`
- App runs on `http://localhost:8000`

Start Adminer (DB UI):

- `docker compose up -d adminer`
- Adminer runs on `http://localhost:8080`
- Login values come from `.env`; for "server" use the service name `postgres`.

Start MQTT ingestion worker:

- `docker compose up -d mqtt_client`

Build images:

- `docker compose build`

Logs:

- `docker compose logs -f backend`
- `docker compose logs -f mqtt_client`

## Django Management Commands (Docker)

Run migrations:

- `docker compose exec backend python manage.py migrate`

Create superuser:

- `docker compose exec backend python manage.py createsuperuser`

Open shell:

- `docker compose exec backend python manage.py shell`

## Test Commands

Test runner is Django's built-in test runner (no pytest config found).

Run all tests:

- `docker compose exec backend python manage.py test`

Run a single app's tests:

- `docker compose exec backend python manage.py test motherplant`

Run a single test class:

- `docker compose exec backend python manage.py test motherplant.tests.MqttClientTests`

Run a single test method:

- `docker compose exec backend python manage.py test motherplant.tests.MqttClientTests.test_parse_topic_valid`

Tips:

- Tests live in `backend/motherplant/tests.py` and use `django.test.TestCase`.
- Keep tests deterministic (timezone-aware datetimes; fixed timestamps).

## Lint / Format

No repo-wide lint/format/type-check tooling is configured yet (no `pyproject.toml`,
`ruff.toml`, `setup.cfg`, etc.).

Until such tooling is added, follow existing code style and keep diffs minimal.

If you introduce tooling, prefer (and commit) explicit config so agents/CI are stable:

- Format: `black`
- Lint: `ruff`
- Imports: `ruff` (or `isort` if preferred)
- Types: `mypy` (requires configuration to be useful)

## Code Style Guidelines

### Python Formatting

- Indentation: 4 spaces. Avoid tabs.
- Keep lines reasonably short (~88-100 chars).
- Use trailing commas in multiline literals/calls to keep diffs clean.

Note: `backend/motherplant/tests.py` currently uses tab indentation; when editing the
file, convert touched blocks to 4-space indentation (do not mix tabs + spaces).

### Imports

Order imports in groups with a blank line between:

1) standard library
2) third-party
3) Django
4) local app/project

Prefer explicit imports over `import *`.

### Naming

- Modules/functions/vars: `snake_case`
- Classes (including Django models): `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Django app labels: lowercase (e.g. `motherplant`)

### Types

- Add type hints for non-trivial helpers and public functions.
- Prefer timezone-aware datetimes (`timezone.utc`).
- Avoid "stringly typed" dicts when a small dataclass/typed object improves clarity.

### Error Handling

- Prefer narrow exceptions (e.g. `except json.JSONDecodeError`) over bare `except`.
- For input validation, log at `warning` and return early (pattern used in MQTT ingest).
- Do not swallow unexpected exceptions silently; either let them raise or log at `error`
  with context and re-raise.

### Logging

- Use `%s` placeholders: `logger.warning("Bad value: %s", value)`.
- Avoid f-strings inside log calls unless you need formatting logic.

### Django Conventions

- Keep business logic in services/commands rather than bloating models.
- Use `get_or_create` for idempotent state creation (already used for `PlantState`).
- Add migrations for model changes and keep them committed.

### API / Serialization

- `djangorestframework` is in requirements but serializers/views are minimal.
- If you add DRF endpoints, keep serializers in `backend/motherplant/serializers.py`
  and route URLs via `backend/planty/urls.py`.

## MQTT Conventions (Project-Specific)

Topic shape (see `mqtt/schemas/topics` and code):

- `planty/{plant_id}/telemetry/{metric}`

Current ingest worker:

- `backend/motherplant/management/commands/mqtt_client.py`
- subscribes to `planty/+/telemetry/+`

Payload:

- expects JSON with `value` (number) and `ts` (unix seconds)

When extending metrics:

- Update `Telemetry.TELEMETRY_TYPES` and any `PlantState.last_*` snapshot fields.
- Decide behavior for unknown metrics: store + ignore snapshot, or reject.

## Repo-Specific Notes / Guardrails

- Cursor rules: none found (`.cursor/rules/` / `.cursorrules` absent).
- Copilot rules: none found (`.github/copilot-instructions.md` absent).
- `.env` exists in-repo with dev defaults; do not add real secrets or production keys.
- `backend/planty/settings.py` contains a hard-coded `SECRET_KEY` (dev only); do not
  replicate this for production configuration.
