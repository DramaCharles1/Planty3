lint:
	ruff check backend/
	ruff check mqtt/core/
	ruff check mqtt/simulator/
	npm --prefix frontend run lint

format:
	ruff format backend/
	ruff check --fix backend/
	ruff format mqtt/core/
	ruff check --fix mqtt/core/
	ruff format mqtt/simulator/
	ruff check --fix mqtt/simulator/
	npm --prefix frontend run format

test:
	docker compose exec backend pytest
	docker run --rm -e PYTHONPATH=/app -v $(PWD)/mqtt/core:/app planty3-simulator-test pytest -v
	docker run --rm -e PYTHONPATH=/app:/app/core -v $(PWD)/mqtt/core:/app/core -v $(PWD)/mqtt/simulator:/app planty3-simulator-test pytest -v
	docker compose exec frontend npm test

coverage:
	docker compose exec backend pytest --cov=motherplant --cov-report=term-missing
	docker run --rm -e PYTHONPATH=/app -v $(PWD)/mqtt/core:/app planty3-simulator-test pytest --cov=core_layer --cov-report=term-missing
	docker run --rm -e PYTHONPATH=/app:/app/core -v $(PWD)/mqtt/core:/app/core -v $(PWD)/mqtt/simulator:/app planty3-simulator-test pytest --cov=plant_simulator --cov-report=term-missing

build-simulator-test:
	cd mqtt/simulator && docker build -t planty3-simulator-test -f Dockerfile .

quality: lint test coverage
