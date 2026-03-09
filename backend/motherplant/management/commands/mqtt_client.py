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
    Expected topic format:
    planty/plant/<plant_id>/telemetry/<metric>
    """
    parts = topic.split("/")

    if len(parts) != 5:
        raise ValueError("Invalid topic format")

    root, entity, plant_id, category, metric = parts

    if root != "planty":
        raise ValueError("Invalid root topic")

    if entity != "plant":
        raise ValueError("Invalid entity type")

    if category != "telemetry":
        raise ValueError("Unsupported category")

    return plant_id, metric


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe("planty/plant/+/telemetry/+")
    else:
        logger.error("MQTT connection failed with code %s", rc)


def on_message(client, userdata, msg):
    logger.debug("Message received: %s %s", msg.topic, msg.payload)

    # ---- Parse topic ----
    try:
        plant_id, metric = parse_topic(msg.topic)
    except ValueError as e:
        logger.warning("Ignoring topic %s: %s", msg.topic, e)
        return

    # ---- Validate metric ----
    allowed_metrics = {"moisture"}
    if metric not in allowed_metrics:
        logger.warning("Rejecting unknown metric %s from %s", metric, msg.topic)
        return

    # ---- Parse payload ----
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from %s", msg.topic)
        return

    value = payload.get("value")
    ts = payload.get("ts")

    if value is None or ts is None:
        logger.warning("Missing fields in payload: %s", payload)
        return

    if not isinstance(value, (int, float)):
        logger.warning("Invalid value type: %s", value)
        return

    try:
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        logger.warning("Invalid timestamp: %s", ts)
        return

    # ---- Plant lookup (must already exist) ----
    try:
        plant = Plant.objects.get(
            plant_id=plant_id,
        )
    except Plant.DoesNotExist:
        logger.warning("Telemetry from unknown or inactive plant: %s", plant_id)
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

    logger.info("Updated %s: %s=%s", plant_id, metric, value)


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
