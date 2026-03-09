import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand

from motherplant.models import Plant, PlantState, Telemetry

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

    Returns: (plant_id, category, metric_or_none)
    """
    parts = topic.split("/")

    if len(parts) < 4 or len(parts) > 5:
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
        return plant_id, category, metric
    elif category == "status":
        if len(parts) != 4:
            raise ValueError("Status topic must be 4 parts")
        return plant_id, category, None
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
        logger.info("Subscribed to telemetry and status topics")
    else:
        logger.error("MQTT connection failed with code %s", rc)


def on_message(client, userdata, msg):
    logger.debug("Message received: %s %s", msg.topic, msg.payload)

    # ---- Parse topic ----
    try:
        plant_id, category, metric = parse_topic(msg.topic)
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
        handle_telemetry(plant, metric, payload)
    elif category == "status":
        handle_status(plant, payload)
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
