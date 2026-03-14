# Planty3
3rd time is the charm

Dockerized Django application with PostgreSQL and MQTT (Mosquitto) for IoT plant monitoring.

## Quick Start

1. **Start all services:**
   ```bash
   docker compose up -d
   ```

2. **Run migrations:**
   ```bash
   docker compose exec backend python manage.py migrate
   ```

3. **Create superuser:**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

4. **Access services:**
   - Django Admin: http://localhost:8000/admin
   - Adminer (DB UI): http://localhost:8080
   - MQTT Broker: localhost:1883

## Docker

Start Docker service:\
`sudo service docker start`

## MQTT

**Mosquitto**

Subscribe to telemetry topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/telemetry/moisture"`

Publish telemetry to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/telemetry/moisture" -m '{"value":45.2,"ts":1766644800}'`

Subscribe to status topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/status"`

Publish status (online) to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/status" -m '{"online":true,"ts":1766644800}' -r`

Publish status (offline) to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/status" -m '{"online":false,"ts":1766644800}' -r`

**Note:** The `-r` flag sets the message as retained, which is recommended for status messages.

Subscribe to command topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/command/+"`

Publish command to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/command/water" -m '{"cmd_id":"test-123","ts":1766644800,"duration":30}' -q 1`

Subscribe to command ack topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/command/+/ack"`

Publish command ack to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/command/water/ack" -m '{"cmd_id":"test-123","ts":1766644800,"ok":true,"error":""}'`

**Note:** Commands use QoS 1 (`-q 1` flag) for reliable delivery.

## Plant Simulator

The plant simulator is a containerized MQTT client that simulates a real plant device for end-to-end testing.

### Quick Start with Simulator

1. **Start all services including simulator:**
   ```bash
   docker compose up -d
   ```

2. **Create a Plant in Django Admin:**
   - Go to http://localhost:8000/admin
   - Navigate to Motherplant > Plants > Add Plant
   - Set `plant_id` to `sim_plant_01` (or your custom `SIM_PLANT_ID`)
   - Set `name` and `location` as desired
   - Save

3. **Watch the simulator in action:**
   ```bash
   docker compose logs -f simulator
   ```

4. **Verify data in database:**
   - Go to Adminer at http://localhost:8080
   - Check `motherplant_telemetry` table for moisture readings
   - Check `motherplant_plantstate` table for online status

### Simulator Behavior

- **Publishes moisture telemetry** every 10 seconds (configurable)
- **Publishes online status** on connect and every 60 seconds
- **Subscribes to commands** on `planty/plant/{plant_id}/command/+`
- **Acknowledges all commands** with `ok: true` (no simulated failures)

### Configuration

Configure the simulator via environment variables in `.env`:

```bash
SIM_PLANT_ID=sim_plant_01              # Plant ID (must exist in database)
SIM_TELEMETRY_INTERVAL=10              # Telemetry interval in seconds
SIM_STATUS_INTERVAL=60                 # Status heartbeat interval in seconds
SIM_MOISTURE_MIN=20.0                  # Minimum moisture value
SIM_MOISTURE_MAX=80.0                  # Maximum moisture value
SIM_MOISTURE_PATTERN=random            # Pattern: random or sine
SIM_LOG_LEVEL=INFO                     # Log level: DEBUG, INFO, WARNING, ERROR
```

See `mqtt/simulator/.env.example` for all available options.

### Testing Commands

Send a test command to the simulator:

```bash
docker compose exec backend python manage.py shell
```

Then in the Django shell:

```python
from motherplant.models import Plant
from motherplant.management.commands.mqtt_client import publish_command
import paho.mqtt.client as mqtt

# Get the plant
plant = Plant.objects.get(plant_id="sim_plant_01")

# Connect and send command
client = mqtt.Client()
client.connect("mqtt", 1883, 60)
publish_command(client, plant, "water", "cmd-001", duration=30)
client.disconnect()
```

Check the simulator logs to see the command received and acknowledged:

```bash
docker compose logs simulator | grep "Received command"
```

Check the database to see the command log:

```bash
# In Django Admin: Motherplant > Command logs
# Or via Adminer: motherplant_commandlog table
```

### Troubleshooting

**Simulator not receiving messages:**
- Ensure the Plant exists in Django Admin with matching `plant_id`
- Check simulator logs: `docker compose logs simulator`
- Check mqtt_client logs: `docker compose logs mqtt_client`

**No telemetry in database:**
- Verify mqtt_client service is running: `docker compose ps mqtt_client`
- Check for errors: `docker compose logs mqtt_client`
- Ensure Plant exists in database

**Command not acknowledged:**
- Check simulator received command: `docker compose logs simulator | grep "Received command"`
- Verify mqtt_client is running: `docker compose ps mqtt_client`
- Check CommandLog in Django Admin

## Database

**Postgre**

1. Start postgre service: `docker compose up postgres`
2. Start Adminer service: `docker compose up adminer`
3. Go to Adminer web interface at `http://localhost:8080`
4. Log in using POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB. Use db service name (postgre) for "server". System should be PostgreSQL.

## Django

**Super user**\
Username: root\
Email address: root@test.com\
Password: password

**Test**\
Run tests for Django motherplant app

***From Docker***\
backend or mqtt_client service must run\
`docker compose exec mqtt_client python manage.py test motherplant`