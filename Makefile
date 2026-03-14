lint:
	ruff check backend/
	ruff check mqtt/simulator/

format:
	ruff format backend/
	ruff check --fix backend/
	ruff format mqtt/simulator/
	ruff check --fix mqtt/simulator/

test:
	docker compose exec backend pytest
	docker run --rm -v $(PWD)/mqtt/simulator:/app planty3-simulator-test pytest -v

coverage:
	docker compose exec backend pytest --cov=motherplant --cov-report=term-missing
	docker run --rm -v $(PWD)/mqtt/simulator:/app planty3-simulator-test pytest --cov=plant_simulator --cov-report=term-missing

build-simulator-test:
	cd mqtt/simulator && docker build -t planty3-simulator-test -f Dockerfile .

quality: lint test coverage
