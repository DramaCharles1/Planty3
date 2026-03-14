#!/usr/bin/env python3
"""
Plant Simulator - Simulates a plant device for end-to-end testing.

This simulator:
- Publishes moisture telemetry at configurable intervals
- Publishes online/offline status messages
- Subscribes to commands and acknowledges them with ok: true
- Connects to MQTT broker as a normal plant device
"""

import datetime
import json
import logging
import math
import os
import random
import signal
import sys
import time
from typing import Optional

import paho.mqtt.client as mqtt


# Configuration from environment variables
PLANT_ID = os.getenv("PLANT_ID", "sim_plant_01")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TELEMETRY_INTERVAL = int(os.getenv("TELEMETRY_INTERVAL", "10"))
STATUS_HEARTBEAT_INTERVAL = int(os.getenv("STATUS_HEARTBEAT_INTERVAL", "60"))
MOISTURE_MIN = float(os.getenv("MOISTURE_MIN", "20.0"))
MOISTURE_MAX = float(os.getenv("MOISTURE_MAX", "80.0"))
MOISTURE_PATTERN = os.getenv("MOISTURE_PATTERN", "random")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("plant_simulator")


def parse_command_topic(topic: str) -> Optional[str]:
    """
    Parse command from topic.

    Expected format: planty/plant/{plant_id}/command/{command}
    Returns command name or None if format doesn't match.
    """
    parts = topic.split("/")
    if (
        len(parts) >= 5
        and parts[0] == "planty"
        and parts[1] == "plant"
        and parts[3] == "command"
    ):
        return parts[4]
    return None


class MoistureSensor:
    """Simulates moisture sensor readings."""

    def __init__(self, min_value: float, max_value: float, pattern: str = "random"):
        self.min_value = min_value
        self.max_value = max_value
        self.pattern = pattern
        self.start_time = time.time()

    def get_reading(self) -> float:
        """Generate a moisture reading based on configured pattern."""
        if self.pattern == "sine":
            return self._sine_mode()
        return self._random_mode()

    def _random_mode(self) -> float:
        """Generate random moisture value in configured range."""
        return random.uniform(self.min_value, self.max_value)

    def _sine_mode(self) -> float:
        """Generate sinusoidal moisture value to simulate drying/watering cycles."""
        elapsed = time.time() - self.start_time
        # Complete cycle every 5 minutes (300 seconds)
        cycle_period = 300
        # Oscillate between min and max
        amplitude = (self.max_value - self.min_value) / 2
        midpoint = self.min_value + amplitude
        value = midpoint + amplitude * math.sin(2 * math.pi * elapsed / cycle_period)
        return value


class PlantSimulator:
    """Main plant simulator class."""

    def __init__(self):
        self.plant_id = PLANT_ID
        self.mqtt_broker_host = MQTT_BROKER_HOST
        self.mqtt_broker_port = MQTT_BROKER_PORT
        self.telemetry_interval = TELEMETRY_INTERVAL
        self.status_heartbeat_interval = STATUS_HEARTBEAT_INTERVAL
        self.shutdown_flag = False

        # Initialize moisture sensor
        self.moisture_sensor = MoistureSensor(
            MOISTURE_MIN, MOISTURE_MAX, MOISTURE_PATTERN
        )

        # Initialize MQTT client
        self.client = mqtt.Client(client_id=f"simulator_{self.plant_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        logger.info(
            "Plant Simulator initialized: plant_id=%s, broker=%s:%s",
            self.plant_id,
            self.mqtt_broker_host,
            self.mqtt_broker_port,
        )

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to commands
            command_topic = f"planty/plant/{self.plant_id}/command/+"
            client.subscribe(command_topic, qos=1)
            logger.info("Subscribed to commands: %s", command_topic)
            # Publish online status
            self.publish_status(online=True)
        else:
            logger.error("Failed to connect to MQTT broker, return code: %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        if rc != 0:
            logger.warning("Unexpected disconnect from MQTT broker, rc=%s", rc)
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info("Received message on topic %s: %s", topic, payload)

            # Parse topic to extract command name
            command = parse_command_topic(topic)
            if command:
                cmd_id = payload.get("cmd_id")

                if cmd_id:
                    logger.info("Received command: %s (cmd_id=%s)", command, cmd_id)
                    # Acknowledge command with ok: true
                    self.publish_command_ack(command, cmd_id)
                else:
                    logger.warning("Command missing cmd_id: %s", payload)
            else:
                logger.warning("Unexpected message topic format: %s", topic)

        except json.JSONDecodeError:
            logger.warning("Invalid JSON payload on topic %s: %s", topic, msg.payload)
        except Exception as e:
            logger.error("Error processing message: %s", e, exc_info=True)

    def publish_telemetry(self) -> None:
        """Publish moisture telemetry reading."""
        moisture_value = self.moisture_sensor.get_reading()
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        topic = f"planty/plant/{self.plant_id}/telemetry/moisture"
        payload = json.dumps({"value": moisture_value, "ts": ts})

        result = self.client.publish(topic, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(
                "Published telemetry: moisture=%.2f to %s", moisture_value, topic
            )
        else:
            logger.error("Failed to publish telemetry, rc=%s", result.rc)

    def publish_status(self, online: bool = True) -> None:
        """Publish online/offline status."""
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        topic = f"planty/plant/{self.plant_id}/status"
        payload = json.dumps({"online": online, "ts": ts})

        result = self.client.publish(topic, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Published status: online=%s to %s", online, topic)
        else:
            logger.error("Failed to publish status, rc=%s", result.rc)

    def publish_command_ack(self, command: str, cmd_id: str) -> None:
        """Publish command acknowledgment with ok: true."""
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        topic = f"planty/plant/{self.plant_id}/command/{command}/ack"
        payload = json.dumps({"cmd_id": cmd_id, "ts": ts, "ok": True, "error": ""})

        result = self.client.publish(topic, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Published ack: %s (cmd_id=%s)", topic, cmd_id)
        else:
            logger.error("Failed to publish ack, rc=%s", result.rc)

    def run(self) -> None:
        """Main run loop."""
        logger.info("Starting plant simulator...")

        # Connect to MQTT broker
        try:
            self.client.connect(self.mqtt_broker_host, self.mqtt_broker_port, 60)
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s", e, exc_info=True)
            return

        # Start MQTT loop in background thread
        self.client.loop_start()

        last_telemetry_time = 0
        last_heartbeat_time = 0

        try:
            while not self.shutdown_flag:
                current_time = time.time()

                # Publish telemetry at configured interval
                if current_time - last_telemetry_time >= self.telemetry_interval:
                    self.publish_telemetry()
                    last_telemetry_time = current_time

                # Publish status heartbeat at configured interval
                if current_time - last_heartbeat_time >= self.status_heartbeat_interval:
                    self.publish_status(online=True)
                    last_heartbeat_time = current_time

                # Sleep briefly to avoid busy loop
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Graceful shutdown - publish offline status and disconnect."""
        logger.info("Shutting down plant simulator...")
        self.publish_status(online=False)
        time.sleep(0.5)  # Give time for message to be sent
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Plant simulator stopped")


# Global simulator instance for signal handler
simulator = None


def signal_handler(signum: int, frame) -> None:
    """Handle SIGTERM and SIGINT for graceful shutdown."""
    logger.info("Received signal %s, shutting down...", signum)
    if simulator:
        simulator.shutdown_flag = True


def main() -> None:
    """Main entry point."""
    global simulator

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and run simulator
    simulator = PlantSimulator()
    simulator.run()

    sys.exit(0)


if __name__ == "__main__":
    main()
