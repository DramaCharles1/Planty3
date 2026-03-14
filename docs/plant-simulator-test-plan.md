# Plant Simulator Test Plan

## Overview

This document outlines the testing strategy for the plant simulator (`mqtt/simulator/plant_simulator.py`). The simulator is a critical component for end-to-end testing of the Planty3 MQTT pipeline, and comprehensive tests are needed to ensure correctness and prevent regressions during future modifications.

## Why Tests Are Important

1. **Verify correctness** - Ensure the simulator behaves as documented
2. **Prevent regressions** - Catch breaking changes when modifying the simulator
3. **Document behavior** - Tests serve as executable specifications
4. **Enable confident refactoring** - Tests provide safety net for code changes

## Testing Approach

Following the project's pytest conventions from `AGENTS.md`:

- Use **pytest + pytest-mock** for testing
- **Mock `paho.mqtt.client.Client`** to avoid real MQTT connections
- Use **`@pytest.mark.parametrize`** for edge cases (invalid payloads, topic formats)
- **Keep tests deterministic** with fixed timestamps (mock `datetime.datetime.now()`)
- **Test in isolation** - no Docker, no real broker needed
- Follow existing test patterns from `backend/motherplant/tests.py`

## Test Infrastructure

### Files to Create

1. **`mqtt/simulator/test_plant_simulator.py`** - main test file
2. **`mqtt/simulator/pytest.ini`** or **`mqtt/simulator/pyproject.toml`** - pytest config
3. Update **`mqtt/simulator/requirements.txt`** to add test dependencies

### Test Dependencies

Add to `mqtt/simulator/requirements.txt`:
```
pytest>=7.4.0
pytest-mock>=3.11.0
pytest-cov>=4.1.0
```

### Running Tests

**Local development:**
```bash
cd mqtt/simulator
pip install -r requirements.txt
pytest -v
```

**With coverage:**
```bash
cd mqtt/simulator
pytest -v --cov=plant_simulator --cov-report=term-missing
```

**Add to Makefile:**
```makefile
test-simulator:
	cd mqtt/simulator && pytest -v

test-simulator-coverage:
	cd mqtt/simulator && pytest -v --cov=plant_simulator --cov-report=term-missing

test-all: test test-simulator
```

**GitHub Actions integration:**
Tests will run in the quality pipeline alongside existing backend tests.

## Code Quality and Formatting

The simulator should follow the same linting and formatting standards as the backend.

### Linting and Formatting Tools

The simulator will use **ruff** for both linting and formatting (same as backend).

Add to `mqtt/simulator/requirements.txt`:
```
ruff>=0.1.0
```

### Running Lint and Format

**Lint simulator code:**
```bash
cd mqtt/simulator
ruff check .
```

**Format simulator code:**
```bash
cd mqtt/simulator
ruff format .
ruff check --fix .
```

### Makefile Integration

Update the Makefile to include simulator in lint and format targets:

```makefile
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
	cd mqtt/simulator && pytest -v

coverage:
	docker compose exec backend pytest --cov=motherplant --cov-report=term-missing
	cd mqtt/simulator && pytest -v --cov=plant_simulator --cov-report=term-missing

quality: lint test coverage
```

This ensures the entire codebase (backend + simulator) follows consistent code quality standards.

## Test Coverage Plan

### 1. MoistureSensor Tests

Test the moisture value generation logic.

#### Test Cases

**`test_random_mode_returns_value_in_range`**
- Create sensor with min=20.0, max=80.0, pattern="random"
- Generate 100 readings
- Assert all values are between 20.0 and 80.0

**`test_sine_mode_returns_value_in_range`**
- Create sensor with min=20.0, max=80.0, pattern="sine"
- Generate 100 readings
- Assert all values are between 20.0 and 80.0

**`test_sine_mode_oscillates_over_time`**
- Create sensor with pattern="sine"
- Take readings at different times
- Assert values change over time (not constant)
- Assert pattern follows sine wave (increases then decreases)

**`test_default_pattern_is_random`**
- Create sensor without specifying pattern
- Verify it defaults to random mode

**`test_random_mode_generates_different_values`**
- Generate multiple readings
- Assert not all values are identical (prove it's random)

### 2. Topic Parsing Tests

Test command topic parsing logic.

#### Test Cases

**`test_parse_command_topic_valid`**
- Input: `"planty/plant/sim_plant_01/command/water"`
- Expected: `"water"`

**`test_parse_command_topic_multiple_commands`**
- Test with various commands: water, calibrate, reset, test_command
- Assert each parses correctly

**`test_parse_command_topic_invalid_format`**
- Input: `"invalid/topic/format"`
- Expected: Should not crash, log warning

**`test_parse_command_topic_missing_command`**
- Input: `"planty/plant/sim_plant_01"`
- Expected: Should not crash, handle gracefully

**`test_parse_command_topic_empty_command`**
- Input: `"planty/plant/sim_plant_01/command/"`
- Expected: Should handle empty command segment

### 3. Payload Generation Tests

Test that published messages have correct structure.

#### Test Cases

**`test_telemetry_payload_structure`**
- Mock publish call
- Verify payload contains:
  - `value` (float)
  - `ts` (int, unix timestamp)
- Verify JSON is valid

**`test_telemetry_payload_topic`**
- Verify topic format: `planty/plant/{plant_id}/telemetry/moisture`
- Verify QoS is 1

**`test_status_payload_structure_online`**
- Mock publish call
- Verify payload contains:
  - `online` (bool, true)
  - `ts` (int, unix timestamp)

**`test_status_payload_structure_offline`**
- Test with `online=False`
- Verify payload has `online: false`

**`test_status_payload_topic`**
- Verify topic format: `planty/plant/{plant_id}/status`
- Verify QoS is 1

**`test_command_ack_payload_structure`**
- Mock publish call
- Verify payload contains:
  - `cmd_id` (string)
  - `ts` (int, unix timestamp)
  - `ok` (bool, always true)
  - `error` (string, empty)

**`test_command_ack_payload_topic`**
- Verify topic format: `planty/plant/{plant_id}/command/{command}/ack`
- Verify QoS is 1

**`test_timestamp_is_unix_epoch`**
- Mock `datetime.datetime.now()` to return fixed time
- Verify `ts` field matches expected unix timestamp (int)

**`test_timestamp_is_utc`**
- Verify timestamps use `datetime.timezone.utc`
- Mock and assert `datetime.datetime.now()` called with timezone.utc

### 4. MQTT Client Behavior Tests (Mocked)

Test simulator's interaction with MQTT broker.

#### Test Cases

**`test_initialization`**
- Create PlantSimulator instance
- Verify client_id format: `simulator_{plant_id}`
- Verify config loaded from environment variables
- Verify callbacks registered

**`test_on_connect_success`**
- Call `_on_connect` with rc=0 (success)
- Assert `client.subscribe()` called once
- Assert subscribe topic: `planty/plant/{plant_id}/command/+`
- Assert QoS 1
- Assert `publish_status(online=True)` called

**`test_on_connect_failure`**
- Call `_on_connect` with rc=5 (auth error)
- Assert error logged
- Assert subscribe NOT called

**`test_on_disconnect_expected`**
- Call `_on_disconnect` with rc=0
- Assert info logged (not warning)

**`test_on_disconnect_unexpected`**
- Call `_on_disconnect` with rc=7 (unexpected)
- Assert warning logged

**`test_on_message_valid_command`**
- Create valid command message
- Topic: `planty/plant/sim_plant_01/command/water`
- Payload: `{"cmd_id": "test-123", "duration": 30}`
- Assert `publish_command_ack()` called with correct args

**`test_on_message_missing_cmd_id`**
- Send command without `cmd_id` field
- Assert warning logged
- Assert ack NOT published

**`test_on_message_invalid_json`**
- Send message with invalid JSON payload
- Assert warning logged
- Assert no crash

**`test_on_message_invalid_topic_format`**
- Send message on unexpected topic
- Assert warning logged
- Assert no crash

**`test_on_message_extracts_command_name`**
- Test with commands: water, calibrate, reset
- Assert each command name extracted correctly from topic

**`test_publish_telemetry_success`**
- Mock `client.publish()` to return success (rc=0)
- Call `publish_telemetry()`
- Assert publish called with correct topic
- Assert payload is valid JSON
- Assert info logged

**`test_publish_telemetry_failure`**
- Mock `client.publish()` to return error (rc=4)
- Call `publish_telemetry()`
- Assert error logged

**`test_publish_status_success`**
- Call `publish_status(online=True)`
- Assert publish called with correct topic
- Assert payload has `online: true`

**`test_publish_command_ack_success`**
- Call `publish_command_ack("water", "cmd-123")`
- Assert publish called with correct topic
- Assert payload structure correct
- Assert `ok: true` always

**`test_shutdown_publishes_offline_and_disconnects`**
- Call `shutdown()`
- Assert `publish_status(online=False)` called
- Assert `client.loop_stop()` called
- Assert `client.disconnect()` called

### 5. Configuration Tests

Test environment variable loading and defaults.

#### Test Cases

**`test_config_defaults`**
- Clear all env vars
- Create PlantSimulator
- Assert defaults:
  - PLANT_ID = "sim_plant_01"
  - MQTT_BROKER_HOST = "mqtt"
  - MQTT_BROKER_PORT = 1883
  - TELEMETRY_INTERVAL = 10
  - STATUS_HEARTBEAT_INTERVAL = 60
  - MOISTURE_MIN = 20.0
  - MOISTURE_MAX = 80.0
  - MOISTURE_PATTERN = "random"

**`test_config_from_environment`**
- Set custom env vars
- Create PlantSimulator
- Assert config matches env vars

**`test_config_port_is_integer`**
- Set MQTT_BROKER_PORT="1883" (string)
- Assert converted to int

**`test_config_intervals_are_integers`**
- Set TELEMETRY_INTERVAL="20" (string)
- Assert converted to int

**`test_config_moisture_values_are_floats`**
- Set MOISTURE_MIN="15.5" (string)
- Assert converted to float

### 6. Integration Tests (Main Loop Behavior)

Test the main run loop without actually running indefinitely.

#### Test Cases

**`test_run_loop_publishes_telemetry_at_interval`**
- Mock time and sleep
- Run loop for simulated 30 seconds
- Assert telemetry published 3 times (at 10s intervals)

**`test_run_loop_publishes_heartbeat_at_interval`**
- Mock time and sleep
- Run loop for simulated 120 seconds
- Assert status published 2 times (at 60s intervals)

**`test_run_loop_handles_shutdown_flag`**
- Start run loop
- Set shutdown_flag=True after 1 iteration
- Assert loop exits cleanly

**`test_run_handles_connection_failure`**
- Mock `client.connect()` to raise exception
- Call `run()`
- Assert error logged
- Assert returns without crashing

### 7. Signal Handling Tests

Test graceful shutdown via signals.

#### Test Cases

**`test_signal_handler_sets_shutdown_flag`**
- Create simulator
- Call `signal_handler(SIGTERM, None)`
- Assert shutdown_flag set to True

**`test_signal_handler_handles_sigint`**
- Test with SIGINT (Ctrl+C)
- Assert shutdown_flag set

**`test_signal_handler_handles_sigterm`**
- Test with SIGTERM (docker stop)
- Assert shutdown_flag set

## Example Test Structure

```python
import pytest
from unittest.mock import MagicMock, patch, call
import json
import time

from plant_simulator import MoistureSensor, PlantSimulator


class TestMoistureSensor:
    def test_random_mode_returns_value_in_range(self):
        """Test random mode generates values between min and max."""
        sensor = MoistureSensor(20.0, 80.0, pattern="random")
        for _ in range(100):
            value = sensor.get_reading()
            assert 20.0 <= value <= 80.0
    
    def test_sine_mode_returns_value_in_range(self):
        """Test sine mode generates values between min and max."""
        sensor = MoistureSensor(20.0, 80.0, pattern="sine")
        for _ in range(100):
            value = sensor.get_reading()
            assert 20.0 <= value <= 80.0
    
    def test_sine_mode_oscillates_over_time(self):
        """Test sine pattern changes over time (not constant)."""
        sensor = MoistureSensor(20.0, 80.0, pattern="sine")
        
        # Get readings at different times
        readings = []
        for _ in range(10):
            readings.append(sensor.get_reading())
            time.sleep(0.1)
        
        # Assert not all values are the same
        assert len(set(readings)) > 1


class TestPlantSimulator:
    @patch('plant_simulator.mqtt.Client')
    def test_on_connect_subscribes_to_commands(self, mock_mqtt_client):
        """Test simulator subscribes to command topic on connect."""
        simulator = PlantSimulator()
        simulator._on_connect(simulator.client, None, None, 0)
        
        # Verify subscribe was called with correct topic
        simulator.client.subscribe.assert_called_once_with(
            "planty/plant/sim_plant_01/command/+", qos=1
        )
    
    @patch('plant_simulator.mqtt.Client')
    def test_on_connect_publishes_online_status(self, mock_mqtt_client):
        """Test simulator publishes online status on connect."""
        simulator = PlantSimulator()
        
        with patch.object(simulator, 'publish_status') as mock_publish_status:
            simulator._on_connect(simulator.client, None, None, 0)
            mock_publish_status.assert_called_once_with(online=True)
    
    @patch('plant_simulator.mqtt.Client')
    @patch('plant_simulator.datetime')
    def test_publish_telemetry_structure(self, mock_datetime, mock_mqtt_client):
        """Test telemetry payload has required fields (value, ts)."""
        # Mock timestamp
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone.utc = None  # Used in function call
        
        simulator = PlantSimulator()
        simulator.publish_telemetry()
        
        # Verify publish was called
        assert simulator.client.publish.called
        call_args = simulator.client.publish.call_args
        
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])
        qos = call_args[1]['qos']
        
        assert topic == "planty/plant/sim_plant_01/telemetry/moisture"
        assert "value" in payload
        assert "ts" in payload
        assert payload["ts"] == 1234567890
        assert isinstance(payload["value"], float)
        assert qos == 1
    
    @patch('plant_simulator.mqtt.Client')
    def test_on_message_parses_and_acks_command(self, mock_mqtt_client):
        """Test simulator acknowledges received commands."""
        simulator = PlantSimulator()
        
        # Create mock message
        mock_msg = MagicMock()
        mock_msg.topic = "planty/plant/sim_plant_01/command/water"
        mock_msg.payload = json.dumps({"cmd_id": "test-123", "duration": 30}).encode('utf-8')
        
        with patch.object(simulator, 'publish_command_ack') as mock_ack:
            simulator._on_message(simulator.client, None, mock_msg)
            mock_ack.assert_called_once_with("water", "test-123")
    
    @patch('plant_simulator.mqtt.Client')
    def test_on_message_handles_invalid_json(self, mock_mqtt_client):
        """Test simulator logs warning for invalid JSON payloads."""
        simulator = PlantSimulator()
        
        # Create mock message with invalid JSON
        mock_msg = MagicMock()
        mock_msg.topic = "planty/plant/sim_plant_01/command/water"
        mock_msg.payload = b"not valid json"
        
        # Should not crash
        simulator._on_message(simulator.client, None, mock_msg)
        # (In real test, would check logger.warning was called)
    
    @patch('plant_simulator.mqtt.Client')
    def test_shutdown_publishes_offline_status(self, mock_mqtt_client):
        """Test simulator publishes offline status on shutdown."""
        simulator = PlantSimulator()
        
        with patch.object(simulator, 'publish_status') as mock_publish_status:
            with patch('plant_simulator.time.sleep'):  # Skip sleep
                simulator.shutdown()
                mock_publish_status.assert_called_once_with(online=False)


class TestConfiguration:
    @patch.dict('os.environ', {}, clear=True)
    @patch('plant_simulator.mqtt.Client')
    def test_config_defaults(self, mock_mqtt_client):
        """Test default configuration values."""
        simulator = PlantSimulator()
        
        assert simulator.plant_id == "sim_plant_01"
        assert simulator.mqtt_broker_host == "mqtt"
        assert simulator.mqtt_broker_port == 1883
        assert simulator.telemetry_interval == 10
        assert simulator.status_heartbeat_interval == 60
    
    @patch.dict('os.environ', {
        'PLANT_ID': 'custom_plant',
        'MQTT_BROKER_HOST': 'custom-mqtt',
        'MQTT_BROKER_PORT': '8883',
        'TELEMETRY_INTERVAL': '20',
    })
    @patch('plant_simulator.mqtt.Client')
    def test_config_from_environment(self, mock_mqtt_client):
        """Test configuration loaded from environment variables."""
        simulator = PlantSimulator()
        
        assert simulator.plant_id == "custom_plant"
        assert simulator.mqtt_broker_host == "custom-mqtt"
        assert simulator.mqtt_broker_port == 8883
        assert simulator.telemetry_interval == 20


@pytest.mark.parametrize("command,expected", [
    ("water", "water"),
    ("calibrate", "calibrate"),
    ("reset", "reset"),
    ("test_command", "test_command"),
])
def test_parse_command_from_topic(command, expected):
    """Test command extraction from various topic formats."""
    topic = f"planty/plant/sim_plant_01/command/{command}"
    parts = topic.split("/")
    if len(parts) >= 5 and parts[3] == "command":
        result = parts[4]
        assert result == expected
```

## Test Execution Strategy

### Development Workflow

1. **During development:**
   ```bash
   cd mqtt/simulator
   pytest -v --tb=short
   ```

2. **Before commit:**
   ```bash
   pytest -v --cov=plant_simulator --cov-report=term-missing
   ```

3. **In CI/CD:**
   ```bash
   make test-simulator  # or integrate into existing `make test`
   ```

### Coverage Goals

- **Minimum coverage:** 80% line coverage
- **Target coverage:** 90%+ line coverage
- **Critical paths:** 100% coverage for:
  - Payload generation (telemetry, status, acks)
  - Topic parsing
  - Message handling callbacks

## Integration with Existing Test Suite

Simulator tests will run locally and in GitHub Actions, not in Docker containers.

### Makefile Integration

Update the `test` target to include simulator tests:

```makefile
test:
	docker compose exec backend pytest
	cd mqtt/simulator && pytest -v

coverage:
	docker compose exec backend pytest --cov=motherplant --cov-report=term-missing
	cd mqtt/simulator && pytest -v --cov=plant_simulator --cov-report=term-missing

quality: lint test coverage
```

This provides a unified test command that runs both backend and simulator tests together.

### GitHub Actions Integration

Add simulator tests to the quality pipeline workflow:

```yaml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      # Install ruff for linting/formatting
      - name: Install ruff
        run: pip install ruff
      
      # Lint and format check (both backend and simulator)
      - name: Run linter
        run: make lint
      
      # Backend tests (existing)
      - name: Run backend tests
        run: |
          docker compose up -d postgres
          docker compose exec backend pytest
      
      # Simulator tests (new)
      - name: Install simulator dependencies
        run: |
          cd mqtt/simulator
          pip install -r requirements.txt
      
      - name: Run simulator tests
        run: |
          cd mqtt/simulator
          pytest -v --cov=plant_simulator --cov-report=term-missing
```

## Success Criteria

Tests are considered complete when:

1. ✅ All test cases outlined above are implemented
2. ✅ Test coverage is ≥80% (target 90%)
3. ✅ All tests pass consistently (deterministic)
4. ✅ Tests run in <10 seconds (no real MQTT, no sleep)
5. ✅ Tests are documented with clear docstrings
6. ✅ Test execution is integrated into project workflow (Makefile/CI)

## Next Steps

1. Review and approve this test plan
2. Implement tests in `mqtt/simulator/test_plant_simulator.py`
3. Add test dependencies to requirements.txt
4. Configure pytest (pytest.ini or pyproject.toml)
5. Integrate test execution into Makefile
6. Run tests and verify coverage
7. Update AGENTS.md with simulator testing documentation

## Notes

- Tests should be added **before merging** the simulator PR or in an immediate follow-up
- Simulator is critical infrastructure for end-to-end testing
- Tests enable confident refactoring and future enhancements
- Follow existing project conventions from `backend/motherplant/tests.py`
