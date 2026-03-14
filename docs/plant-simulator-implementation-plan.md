# Plant Simulator Implementation Plan

## Overview

This document outlines the implementation plan for a plant simulator that enables end-to-end testing of the Planty3 MQTT → Django pipeline.

## Requirements

- Simulator must connect to the MQTT broker as a normal plant device
- Must handle all allowed message types (telemetry, status, commands, acks)
- Must be seen as a normal plant by the motherplant backend
- Plant record must be created via Django Admin (no auto-setup)
- Always acknowledge commands with `ok: true` (no failure simulation)
- No artificial delay for command acknowledgments
- Must run as a Docker Compose service

---

## Implementation Tasks

### 1. Design simulator architecture and configuration

**File location:** `mqtt/simulator/plant_simulator.py`

**Core functionality:**
- Single Python script using `paho-mqtt`
- Operates as a long-running process (infinite loop with sleep intervals)
- Implements a stateful virtual plant device

**Simulator behaviors:**

**A. Telemetry publishing (moisture)**
- Publish to: `planty/plant/{plant_id}/telemetry/moisture`
- Payload: `{"value": <float>, "ts": <unix_epoch>}`
- Strategy: Generate realistic moisture values (e.g., random in range 0-100, or sinusoidal pattern to simulate drying/watering cycles)
- Interval: Configurable (default every 10 seconds)

**B. Status publishing (online/offline)**
- Publish to: `planty/plant/{plant_id}/status`
- Payload: `{"online": true, "ts": <unix_epoch>}`
- Publish on connect (announce online presence)
- Optionally publish periodic heartbeat (every 60 seconds)
- Publish `{"online": false, "ts": <unix_epoch>}` on graceful shutdown (optional, but nice for testing)

**C. Command subscription**
- Subscribe to: `planty/plant/{plant_id}/command/+`
- On receiving any command message, parse the payload to extract `cmd_id`
- Immediately publish ack

**D. Command acknowledgment**
- Publish to: `planty/plant/{plant_id}/command/{command}/ack`
- Payload: `{"cmd_id": <cmd_id_from_command>, "ts": <unix_epoch>, "ok": true, "error": ""}`
- Always succeed (no failure simulation needed)

**Configuration via environment variables:**
- `PLANT_ID` (required, default: `"sim_plant_01"`)
- `MQTT_BROKER_HOST` (default: `"mqtt"`)
- `MQTT_BROKER_PORT` (default: `1883`)
- `TELEMETRY_INTERVAL` (default: `10` seconds)
- `STATUS_HEARTBEAT_INTERVAL` (default: `60` seconds)
- `MOISTURE_MIN` (default: `20.0`)
- `MOISTURE_MAX` (default: `80.0`)
- `MOISTURE_PATTERN` (default: `"random"`, options: `"random"`, `"sine"`)

**Logging:**
- Use Python `logging` module
- Log level configurable via `LOG_LEVEL` (default: `INFO`)
- Log all published messages (topic + payload summary)
- Log all received commands

**Signal handling:**
- Catch `SIGTERM` and `SIGINT`
- On shutdown: publish offline status, disconnect cleanly, exit

---

### 2. Create simulator Python script with MQTT client

**File:** `mqtt/simulator/plant_simulator.py`

**Structure:**
```
- Imports (paho.mqtt, json, time, logging, signal, os, datetime, random, math)
- Configuration loading (from env vars)
- Logger setup
- MoistureSensor class (encapsulates value generation logic)
  - random_mode(): returns random float in [min, max]
  - sine_mode(): returns sinusoidal value that oscillates over time
- PlantSimulator class
  - __init__(): read config, setup mqtt client, setup moisture sensor
  - on_connect(): subscribe to commands, publish online status
  - on_message(): handle incoming commands, publish acks
  - on_disconnect(): log disconnect
  - publish_telemetry(): publish moisture reading
  - publish_status(online=True): publish status
  - publish_command_ack(command, cmd_id): publish ack with ok=true
  - run(): main loop (connect, publish telemetry on interval, loop_start, sleep, repeat)
  - shutdown(): cleanup (publish offline, disconnect)
- signal_handler(): set shutdown flag
- main(): instantiate simulator, register signal handler, run
- if __name__ == "__main__": main()
```

**Key implementation notes:**
- Use `client.loop_start()` (background thread) so we can sleep in the main loop without blocking MQTT
- Use a shutdown flag checked in the main loop
- Extract command name from topic in `on_message` (split by `/`, take index 5)
- Use `datetime.datetime.now(datetime.timezone.utc).timestamp()` for all `ts` fields
- Use QoS 1 for all publishes (matches the system's command QoS)

---

### 3. Add simulator configuration and dependencies

**File:** `mqtt/simulator/requirements.txt`
```
paho-mqtt==2.1.0
```

This is the only runtime dependency. The simulator should be self-contained.

**Optional file:** `mqtt/simulator/.env.example`
```
PLANT_ID=sim_plant_01
MQTT_BROKER_HOST=mqtt
MQTT_BROKER_PORT=1883
TELEMETRY_INTERVAL=10
STATUS_HEARTBEAT_INTERVAL=60
MOISTURE_MIN=20.0
MOISTURE_MAX=80.0
MOISTURE_PATTERN=random
LOG_LEVEL=INFO
```

This documents the available config options.

---

### 4. Integrate simulator into docker-compose.yaml

**Add new service:** `simulator`

**Service definition:**
```yaml
simulator:
  build:
    context: ./mqtt/simulator
    dockerfile: Dockerfile
  container_name: planty3-simulator
  environment:
    PLANT_ID: ${SIM_PLANT_ID:-sim_plant_01}
    MQTT_BROKER_HOST: mqtt
    MQTT_BROKER_PORT: 1883
    TELEMETRY_INTERVAL: ${SIM_TELEMETRY_INTERVAL:-10}
    STATUS_HEARTBEAT_INTERVAL: ${SIM_STATUS_INTERVAL:-60}
    MOISTURE_MIN: ${SIM_MOISTURE_MIN:-20.0}
    MOISTURE_MAX: ${SIM_MOISTURE_MAX:-80.0}
    MOISTURE_PATTERN: ${SIM_MOISTURE_PATTERN:-random}
    LOG_LEVEL: ${SIM_LOG_LEVEL:-INFO}
  depends_on:
    mqtt:
      condition: service_started
  restart: unless-stopped
  networks:
    - default
```

**Create Dockerfile:** `mqtt/simulator/Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY plant_simulator.py .

CMD ["python", "-u", "plant_simulator.py"]
```

**Notes:**
- Use `python -u` for unbuffered output (logs appear immediately in `docker compose logs`)
- Use `restart: unless-stopped` for resilience (same as `mqtt_client`)
- Link to `.env` for default values (add `SIM_*` vars to `.env` optionally)
- No volume mount needed (simulator is stateless, no code editing expected)
- Depends on `mqtt` but not on `postgres` (simulator is a pure MQTT client)

---

### 5. Update documentation (AGENTS.md, README if exists)

**Update AGENTS.md:**

Add a new section under "## Quick Orientation" or "## Repo-Specific Notes":

```markdown
## Plant Simulator

A simulated plant device for end-to-end testing.

Location: `mqtt/simulator/plant_simulator.py`

Start simulator:
- `docker compose up -d simulator`

Logs:
- `docker compose logs -f simulator`

**Prerequisites:**
- The Plant record must exist in Django. Use Django Admin to create a Plant with `plant_id` matching `SIM_PLANT_ID` (default: `sim_plant_01`).

**Behavior:**
- Publishes moisture telemetry every `TELEMETRY_INTERVAL` seconds (default: 10s)
- Publishes online status on connect and every `STATUS_HEARTBEAT_INTERVAL` seconds (default: 60s)
- Subscribes to commands on `planty/plant/{plant_id}/command/+`
- Acknowledges all commands with `ok: true` (no simulated failures)

**Configuration:**
See `mqtt/simulator/.env.example` for available environment variables.

**Testing end-to-end:**
1. Start services: `docker compose up -d mqtt postgres backend mqtt_client simulator`
2. Create a Plant in Django Admin with `plant_id = "sim_plant_01"`
3. Watch simulator logs: `docker compose logs -f simulator`
4. Watch mqtt_client logs: `docker compose logs -f mqtt_client`
5. Check Adminer or Django Admin to see `Telemetry` and `PlantState` records
6. Send a command via Django shell or future API (Phase 4)
```

**Optional:** If there's a top-level `README.md`, add a similar section under a "Testing" or "Development" heading.

---

### 6. Test simulator end-to-end with mqtt_client worker

**Manual test procedure (after implementation):**

**Step 1: Build and start all services**
```bash
docker compose build
docker compose up -d
```

**Step 2: Create Plant in Django Admin**
- Open `http://localhost:8000/admin`
- Login with superuser (create one if needed: `docker compose exec backend python manage.py createsuperuser`)
- Navigate to `Motherplant > Plants > Add Plant`
- Set `plant_id = "sim_plant_01"`, `name = "Simulated Plant"`, `location = "Test Lab"`
- Save

**Step 3: Verify simulator is publishing**
```bash
docker compose logs -f simulator
```
Expected: Logs showing "Published telemetry" every 10 seconds

**Step 4: Verify mqtt_client is receiving**
```bash
docker compose logs -f mqtt_client
```
Expected: No warnings about unknown plants; should be silent (only logs on connect or errors)

**Step 5: Check database via Adminer**
- Open `http://localhost:8080`
- Login (server: `postgres`, username: `planty_user`, password: `planty_pass`, database: `planty_db`)
- Check `motherplant_telemetry` table -- should have rows with `plant_id=1`, `type='moisture'`, timestamps
- Check `motherplant_plantstate` table -- should have one row with `plant_id=1`, `online=true`, `last_moisture` populated

**Step 6: Test command flow**
```bash
docker compose exec backend python manage.py shell
```
```python
from motherplant.models import Plant
from motherplant.management.commands.mqtt_client import publish_command
import paho.mqtt.client as mqtt

plant = Plant.objects.get(plant_id="sim_plant_01")
client = mqtt.Client()
client.connect("mqtt", 1883)
publish_command(client, plant, "water", "test-cmd-001", duration=30)
client.disconnect()
```

Then check:
- Simulator logs: should show "Received command: water"
- Simulator logs: should show "Published ack: water/ack"
- mqtt_client logs: should show no errors
- Django Admin > Command logs: should have one row with `cmd_id="test-cmd-001"`, `ok=True`

**Step 7: Run existing unit tests**
```bash
make test
```
Expected: All 11 tests pass (simulator does not affect unit tests, which are fully mocked)

**Step 8: Run quality checks**
```bash
make quality
```
Expected: lint, test, and coverage all pass

---

## Summary

This plan creates a **standalone, dockerized plant simulator** that:
- ✅ Connects to the MQTT broker as a real plant would
- ✅ Publishes telemetry and status messages
- ✅ Subscribes to commands and sends acks
- ✅ Requires Plant to be pre-created in Django (no auto-setup)
- ✅ Always acks with `ok: true` (no failure simulation)
- ✅ Has no built-in delay (immediate ack)
- ✅ Runs as a Docker Compose service
- ✅ Is configurable via environment variables
- ✅ Enables full end-to-end manual testing of the MQTT → Django pipeline

---

## Files to Create

1. `mqtt/simulator/plant_simulator.py` (~200-250 lines)
2. `mqtt/simulator/Dockerfile` (~8 lines)
3. `mqtt/simulator/requirements.txt` (1 line)
4. `mqtt/simulator/.env.example` (~10 lines)

## Files to Modify

1. `docker-compose.yaml` (add `simulator` service)
2. `AGENTS.md` (add simulator documentation section)

---

## Next Steps

Ready to proceed with implementation when approved.
