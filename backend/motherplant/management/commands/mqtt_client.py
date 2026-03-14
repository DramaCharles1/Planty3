import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand

from motherplant.models import CommandLog, Plant, PlantState, Telemetry

# -------------------------------------------------
# Logging
# -------------------------------------------------
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Topic parsing
# -------------------------------------------------
def parse_topic(topic: str):
    """
    Expected topic formats:
    - planty/plant/<plant_id>/telemetry/<metric>
    - planty/plant/<plant_id>/status
    - planty/plant/<plant_id>/command/<command>
    - planty/plant/<plant_id>/command/<command>/ack

    Returns: (plant_id, category, subcategory_or_none, command_or_metric_or_none)
    """
    parts = topic.split("/")

    if len(parts) < 4 or len(parts) > 6:
        raise ValueError("Invalid topic format")

    root, entity, plant_id, category = parts[:4]

    if root != "planty":
        raise ValueError("Invalid root topic")

    if entity != "plant":
        raise ValueError("Invalid entity type")

    if category == "telemetry":
        if len(parts) != 5:
            raise ValueError("Telemetry topic requires metric")
        metric = parts[4]
        return plant_id, category, None, metric
    elif category == "status":
        if len(parts) != 4:
            raise ValueError("Status topic must be 4 parts")
        return plant_id, category, None, None
    elif category == "command":
        if len(parts) < 5:
            raise ValueError("Command topic requires command name")
        command = parts[4]
        # Check if this is an ack topic
        if len(parts) == 6:
            if parts[5] == "ack":
                return plant_id, category, "ack", command
            else:
                raise ValueError("Invalid command subtopic")
        return plant_id, category, None, command
    else:
        raise ValueError(f"Unsupported category: {category}")


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe("planty/plant/+/telemetry/+")
        client.subscribe("planty/plant/+/status")
        client.subscribe("planty/plant/+/command/+/ack")
        logger.info("Subscribed to telemetry, status, and command ack topics")
    else:
        logger.error("MQTT connection failed with code %s", rc)


def on_message(client, userdata, msg):
    logger.debug("Message received: %s %s", msg.topic, msg.payload)

    # ---- Parse topic ----
    try:
        plant_id, category, subcategory, command_or_metric = parse_topic(msg.topic)
    except ValueError as e:
        logger.warning("Ignoring topic %s: %s", msg.topic, e)
        return

    # ---- Parse payload ----
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from %s", msg.topic)
        return

    # ---- Plant lookup (must already exist) ----
    try:
        plant = Plant.objects.get(plant_id=plant_id)
    except Plant.DoesNotExist:
        logger.warning("Message from unknown plant: %s", plant_id)
        return

    # ---- Handle by category ----
    if category == "telemetry":
        handle_telemetry(plant, command_or_metric, payload)
    elif category == "status":
        handle_status(plant, payload)
    elif category == "command":
        if subcategory == "ack":
            handle_command_ack(plant, command_or_metric, payload)
        else:
            # Commands sent FROM motherplant TO device
            # We don't expect to receive non-ack commands here
            logger.warning("Unexpected command message on %s", msg.topic)
    else:
        logger.warning("Unsupported category: %s", category)


def handle_telemetry(plant, metric, payload):
    """Handle telemetry messages."""
    # ---- Validate metric ----
    allowed_metrics = {"moisture"}
    if metric not in allowed_metrics:
        logger.warning("Rejecting unknown metric %s for %s", metric, plant.plant_id)
        return

    value = payload.get("value")
    ts = payload.get("ts")

    if value is None or ts is None:
        logger.warning("Missing fields in telemetry payload: %s", payload)
        return

    if not isinstance(value, (int, float)):
        logger.warning("Invalid value type: %s", value)
        return

    try:
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        logger.warning("Invalid timestamp: %s", ts)
        return

    # ---- Store telemetry history ----
    Telemetry.objects.create(
        plant=plant,
        type=metric,
        value=value,
        timestamp=timestamp,
    )

    # ---- Update plant snapshot ----
    state, _ = PlantState.objects.get_or_create(plant=plant)

    if metric == "moisture":
        state.last_moisture = value

    state.save()

    logger.info("Updated %s: %s=%s", plant.plant_id, metric, value)


def handle_status(plant, payload):
    """Handle status messages (online/offline presence)."""
    online = payload.get("online")
    ts = payload.get("ts")

    if online is None or ts is None:
        logger.warning("Missing fields in status payload: %s", payload)
        return

    if not isinstance(online, bool):
        logger.warning("Invalid online type: %s", online)
        return

    try:
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        logger.warning("Invalid timestamp: %s", ts)
        return

    # ---- Update plant state ----
    state, _ = PlantState.objects.get_or_create(plant=plant)
    state.online = online
    state.last_seen = timestamp
    state.save()

    status_str = "online" if online else "offline"
    logger.info("Plant %s is now %s (last_seen=%s)", plant.plant_id, status_str, timestamp)


def handle_command_ack(plant, command, payload):
    """Handle command acknowledgment messages from devices."""
    cmd_id = payload.get("cmd_id")
    ts = payload.get("ts")
    ok = payload.get("ok")
    error = payload.get("error", "")

    if cmd_id is None or ts is None or ok is None:
        logger.warning("Missing fields in command ack payload: %s", payload)
        return

    if not isinstance(ok, bool):
        logger.warning("Invalid ok type: %s", ok)
        return

    try:
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        logger.warning("Invalid timestamp: %s", ts)
        return

    # ---- Find and update command log ----
    try:
        cmd_log = CommandLog.objects.get(plant=plant, cmd_id=cmd_id, command=command)
        cmd_log.ack_at = timestamp
        cmd_log.ok = ok
        cmd_log.error = error
        cmd_log.save()

        status_str = "succeeded" if ok else f"failed: {error}"
        logger.info("Command %s/%s ack received: %s", plant.plant_id, command, status_str)
    except CommandLog.DoesNotExist:
        logger.warning("Received ack for unknown command: %s %s", plant.plant_id, cmd_id)
    except CommandLog.MultipleObjectsReturned:
        logger.error("Multiple command logs found for %s %s", plant.plant_id, cmd_id)


def publish_command(client, plant, command, cmd_id, **kwargs):
    """
    Helper function to publish a command to a device and log it.

    Args:
        client: MQTT client instance
        plant: Plant model instance
        command: Command name (e.g., 'water', 'calibrate')
        cmd_id: Unique command ID (UUID or int)
        **kwargs: Additional command arguments to include in payload
    """
    topic = f"planty/plant/{plant.plant_id}/command/{command}"

    payload = {
        "cmd_id": str(cmd_id),
        "ts": int(datetime.now(tz=timezone.utc).timestamp()),
        **kwargs,
    }

    # ---- Log command ----
    CommandLog.objects.create(
        plant=plant,
        command=command,
        cmd_id=str(cmd_id),
        sent_at=datetime.now(tz=timezone.utc),
        raw_payload=payload,
    )

    # ---- Publish to MQTT ----
    result = client.publish(topic, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logger.info("Command sent: %s/%s (cmd_id=%s)", plant.plant_id, command, cmd_id)
    else:
        logger.error("Failed to send command: %s/%s", plant.plant_id, command)

    return result


# -------------------------------------------------
# Django management command
# -------------------------------------------------
class Command(BaseCommand):
    help = "Run MQTT worker for plant telemetry ingestion"

    def handle(self, *args, **options):
        logger.info("Starting MQTT worker")

        client = mqtt.Client()

        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            keepalive=60,
        )

        client.loop_forever()
