import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from backend.motherplant.models import Plant, PlantState, Telemetry


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
    planty/<plant_id>/telemetry/<metric>
    """
    parts = topic.split("/")

    if len(parts) != 4:
        raise ValueError("Invalid topic format")

    root, plant_id, category, metric = parts

    if root != "planty":
        raise ValueError("Invalid root topic")

    if category != "telemetry":
        raise ValueError("Unsupported category")

    return plant_id, metric


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe("planty/+/telemetry/+")
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
        timestamp = make_aware(
            datetime.fromtimestamp(ts, tz=timezone.utc)
        )
    except Exception:
        logger.warning("Invalid timestamp: %s", ts)
        return

    # ---- Plant lookup (must already exist) ----
    try:
        plant = Plant.objects.get(
            plant_id=plant_id,
            is_active=True
        )
    except Plant.DoesNotExist:
        logger.warning(
            "Telemetry from unknown or inactive plant: %s",
            plant_id
        )
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

    if metric == "temperature":
        state.last_temperature = value
    elif metric == "moisture":
        state.last_moisture = value
    elif metric == "battery":
        state.battery_level = value
    else:
        logger.info("Unhandled metric type: %s", metric)

    state.last_seen = datetime.now(timezone.utc)
    state.online = True
    state.save()

    logger.info(
        "Updated %s: %s=%s",
        plant_id,
        metric,
        value
    )


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
