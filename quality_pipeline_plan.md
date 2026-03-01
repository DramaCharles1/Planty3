# Quality Pipeline and CI Plan

## Overview
Add a quality pipeline with code coverage, static code analysis (linting), and testing. Start manual/local, then add CI for PR enforcement.

## Execution Environment (Hybrid Approach)

Lint and format run **on the host** (fast, no Docker needed). Tests run **inside Docker** (need Postgres + MQTT).

- **Host**: ruff (lint/format) -- requires a local Python install but no virtualenv for the project itself.
- **Docker**: pytest + pytest-django -- run via `docker compose exec backend pytest` to access Postgres.
- **Makefile**: Wraps both host and Docker commands behind a unified interface.

## Dependencies

Separate dev dependencies from production:

- `requirements.txt`: Production dependencies only (Django, psycopg, paho-mqtt, etc.).
- `requirements-dev.txt`: Starts with `-r requirements.txt`, then adds pytest, pytest-django, pytest-cov, ruff.
- **Dockerfile**: Change to install `requirements-dev.txt` directly. This is a dev-only project with no production deployment; no need for build args or multi-stage builds. Revisit if/when a production image is needed.

## Phase 1a: Tooling Setup

- **Config**: Single `pyproject.toml` at `backend/` for pytest, coverage, and ruff.
- **Ruff config** (in `pyproject.toml`):
  - Rule sets: `E`, `F`, `W`, `I` (errors, pyflakes, warnings, import sorting).
  - `line-length = 100` (matches AGENTS.md "~88-100 chars" guideline).
  - `target-version = "py312"`.
  - Exclude: `migrations/`.
- **Test runner**: pytest + pytest-django.
  - `manage.py test` is retired; `pytest` is the single test command going forward.
  - pytest-django handles test DB creation, teardown, and Django setup automatically.
  - Existing `django.test.TestCase` subclasses run under pytest unchanged -- no rewrite needed.
- **pytest config** (in `pyproject.toml`):
  - `DJANGO_SETTINGS_MODULE = "planty.settings"` -- this is all pytest-django needs.
  - No `conftest.py` required for basic setup (pytest-django reads the setting from `pyproject.toml`).
  - Convert `tests.py` tab indentation to 4 spaces.
- **Makefile targets** (require `docker compose up -d backend postgres` running):
  - `make lint` -- run ruff check on host.
  - `make format` -- run ruff format + ruff check --fix on host.
  - `make test` -- run `docker compose exec backend pytest`.
  - `make coverage` -- run `docker compose exec backend pytest --cov`, print report.
  - `make quality` -- run lint + test + coverage in sequence.
- **Run**: Locally via `make lint`, `make test`, etc. Docker targets require backend and postgres containers to be running.

### Acceptance Criteria (Phase 1a is done when)

1. `make lint` runs ruff and reports results (existing findings are fine -- the tooling works).
2. `make test` runs the existing 4 tests under pytest and all pass.
3. `make coverage` prints a coverage report.
4. `pyproject.toml` is committed with ruff, pytest, and coverage config.
5. `requirements-dev.txt` exists and Dockerfile installs it.
6. `tests.py` tab indentation is converted to 4 spaces.
7. AGENTS.md is updated with new commands.

## Tests

No new tests are written as part of this plan. Existing tests run under pytest as-is to validate the tooling works.

Test coverage will be built up as part of the topic remake phases -- writing tests against code that's about to change in the topic remake is wasted effort. Coverage baseline and targets will be established once meaningful tests exist after the topic remake.

## Phase 2: CI for PR Enforcement
- **Tool**: GitHub Actions.
- **Setup**:
  - `.github/workflows/ci.yml`: Run lint (host-style, no Docker needed) and tests + coverage (via Docker Compose or a Postgres service container) on push/PR.
  - Branch protection: Require CI to pass before merge.
- **Run**: Automatic on PRs.
- **Verify**: PRs blocked if lint or tests fail.

## Pre-commit Hooks
Deferred. Add pre-commit hooks for ruff when multiple contributors join the project. Until then, CI enforcement (Phase 2) catches the same issues without local friction.

## Integration
- Phase 1a (tooling) before Phase 2 (CI), both before topic remake Phase 1.
- Tests are written/updated as part of each topic remake phase.
- Update AGENTS.md with new commands after Phase 1a.
