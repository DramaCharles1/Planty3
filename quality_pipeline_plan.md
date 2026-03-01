# Quality Pipeline and CI Plan

## Overview
Add a quality pipeline with code coverage, static code analysis (linting), and testing. Start manual/local, then add CI for PR enforcement.

## Phase 1: Quality Pipeline (Manual/Local)
- **Tools**: pytest (tests), coverage.py (coverage), ruff (linting/formatting).
- **Setup**:
  - Install: pytest, pytest-django, pytest-cov, coverage, ruff.
  - Config: pyproject.toml for pytest, coverage, ruff.
  - Commands: Makefile with `lint`, `coverage`, `test`, `quality`.
  - Pre-commit: Hooks for ruff and coverage.
- **Run**: Locally via `make lint`, `make coverage`, `make test`.
- **Verify**: Coverage >=80%, lint passes.

## Phase 2: CI for PR Enforcement
- **Tool**: GitHub Actions (free for public repos).
- **Setup**:
  - .github/workflows/ci.yml: Run lint, coverage, test on push/PR.
  - Branch protection: Require CI to pass.
- **Run**: Automatic on PRs.
- **Verify**: PRs blocked if fails.

## Integration
- Phase 1 before Phase 2; both before MQTT topic Phase 1.
- Update AGENTS.md with commands.