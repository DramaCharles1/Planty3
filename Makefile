lint:
	ruff check backend/

format:
	ruff format backend/
	ruff check --fix backend/

test:
	docker compose exec backend pytest

coverage:
	docker compose exec backend pytest --cov

quality: lint test coverage