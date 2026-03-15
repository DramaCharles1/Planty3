"""
Service layer for business logic.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from .models import CommandLog, Plant

logger = logging.getLogger(__name__)


def get_mqtt_client():
    """
    Create and return a configured MQTT client.
    Not connected - caller should connect before use.
    """
    mqtt_host = os.getenv("MQTT_HOST", "mqtt")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))

    client = mqtt.Client()
    client.connect(mqtt_host, mqtt_port, 60)
    return client


def send_command(plant: Plant, command: str, **kwargs) -> CommandLog:
    """
    Send a command to a plant device via MQTT and log it.

    Args:
        plant: Plant instance to send command to
        command: Command name (e.g., 'water')
        **kwargs: Additional command arguments

    Returns:
        CommandLog instance for the sent command

    Raises:
        Exception: If MQTT publish fails
    """
    cmd_id = str(uuid.uuid4())
    topic = f"planty/plant/{plant.plant_id}/command/{command}"

    payload = {
        "cmd_id": cmd_id,
        "ts": int(datetime.now(tz=timezone.utc).timestamp()),
        **kwargs,
    }

    # Create command log
    command_log = CommandLog.objects.create(
        plant=plant,
        command=command,
        cmd_id=cmd_id,
        sent_at=datetime.now(tz=timezone.utc),
        raw_payload=payload,
    )

    # Publish to MQTT
    try:
        client = get_mqtt_client()
        result = client.publish(topic, json.dumps(payload), qos=1)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                "Failed to publish command %s to plant %s: rc=%s",
                command,
                plant.plant_id,
                result.rc,
            )
            raise Exception(f"MQTT publish failed with code {result.rc}")

        client.disconnect()
        logger.info(
            "Published command %s to plant %s with cmd_id=%s",
            command,
            plant.plant_id,
            cmd_id,
        )

    except Exception:
        logger.exception("Exception publishing command to MQTT")
        # Delete the command log if publish failed
        command_log.delete()
        raise

    return command_log
