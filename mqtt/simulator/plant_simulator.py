#!/usr/bin/env python3
"""
Plant Simulator - Simulates a plant device for end-to-end testing.

This simulator uses the core layer as an adapter, demonstrating how to integrate
the platform-agnostic core with a real MQTT client.

Adapter responsibilities:
- Translate paho.mqtt.client callbacks into core events
- Execute core actions (Publish, ExecuteCommand, Log)
- Generate sensor events (MetricSample)
- Handle Tick events for periodic telemetry/heartbeat
- Manage lifecycle: boot → connect → run loop → shutdown
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

# Import core layer - handle both test and runtime environments
try:
    # Try direct import first (works when PYTHONPATH includes core)
    from core_layer import (
        Action,
        Booted,
        CommandResult,
        CoreConfig,
        CoreLayer,
        ExecuteCommand,
        Log,
        MetricSample,
        MqttConnected,
        MqttDisconnected,
        MqttMessage,
        Publish,
        Tick,
    )
except ImportError:
    # Fall back to relative path for runtime
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
    from core_layer import (
        Action,
        Booted,
        CommandResult,
        CoreConfig,
        CoreLayer,
        ExecuteCommand,
        Log,
        MetricSample,
        MqttConnected,
        MqttDisconnected,
        MqttMessage,
        Publish,
        Tick,
    )


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
    """
    Plant simulator adapter using core layer.

    This adapter:
    - Translates MQTT callbacks to core events
    - Executes core actions (Publish, ExecuteCommand, Log)
    - Generates sensor events (MetricSample)
    - Maintains existing simulator behavior
    """

    def __init__(self):
        self.plant_id = PLANT_ID
        self.mqtt_broker_host = MQTT_BROKER_HOST
        self.mqtt_broker_port = MQTT_BROKER_PORT
        self.telemetry_interval = TELEMETRY_INTERVAL
        self.status_heartbeat_interval = STATUS_HEARTBEAT_INTERVAL
        self.shutdown_flag = False

        # Initialize core layer with config
        config = CoreConfig(plant_id=self.plant_id)
        self.core = CoreLayer(config=config)

        # Initialize moisture sensor
        self.moisture_sensor = MoistureSensor(
            MOISTURE_MIN, MOISTURE_MAX, MOISTURE_PATTERN
        )

        # Initialize MQTT client
        self.client = mqtt.Client(client_id=f"simulator_{self.plant_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Process boot event
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        actions = self.core.handle_event(Booted(ts=ts))
        self._execute_actions(actions)

        logger.info(
            "Plant Simulator initialized: plant_id=%s, broker=%s:%s",
            self.plant_id,
            self.mqtt_broker_host,
            self.mqtt_broker_port,
        )

    def _execute_actions(self, actions: list[Action]) -> None:
        """Execute actions returned by core layer."""
        for action in actions:
            if isinstance(action, Publish):
                self._execute_publish(action)
            elif isinstance(action, ExecuteCommand):
                self._execute_command(action)
            elif isinstance(action, Log):
                self._execute_log(action)
            else:
                logger.warning("Unknown action type: %s", type(action))

    def _execute_publish(self, action: Publish) -> None:
        """Execute Publish action via MQTT client."""
        result = self.client.publish(
            action.topic, action.payload_bytes, qos=action.qos, retain=action.retain
        )
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(
                "Published to %s (qos=%d, retain=%s): %s",
                action.topic,
                action.qos,
                action.retain,
                action.payload_bytes.decode("utf-8"),
            )
        else:
            logger.error("Failed to publish to %s, rc=%s", action.topic, result.rc)

    def _execute_command(self, action: ExecuteCommand) -> None:
        """
        Execute command action (simulate actuator).

        For simulator, all commands succeed immediately.
        """
        logger.info(
            "Executing command: %s (cmd_id=%s, args=%s)",
            action.command,
            action.cmd_id,
            action.args,
        )

        # Simulate command execution (always succeeds for simulator)
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        result = CommandResult(
            cmd_id=action.cmd_id, command=action.command, ok=True, error=None, ts=ts
        )
        actions = self.core.handle_event(result)
        self._execute_actions(actions)

    def _execute_log(self, action: Log) -> None:
        """Execute Log action via Python logging."""
        log_method = getattr(logger, action.level.lower(), logger.info)
        log_method("%s", action.message, extra=action.fields)

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to commands
            command_topic = f"planty/plant/{self.plant_id}/command/+"
            client.subscribe(command_topic, qos=1)
            logger.info("Subscribed to commands: %s", command_topic)

            # Send MqttConnected event to core
            ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            actions = self.core.handle_event(MqttConnected(ts=ts))
            self._execute_actions(actions)
        else:
            logger.error("Failed to connect to MQTT broker, return code: %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        if rc != 0:
            logger.warning("Unexpected disconnect from MQTT broker, rc=%s", rc)
        else:
            logger.info("Disconnected from MQTT broker")

        # Send MqttDisconnected event to core
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        actions = self.core.handle_event(MqttDisconnected(ts=ts))
        self._execute_actions(actions)

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        topic = msg.topic
        try:
            payload_bytes = msg.payload
            ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

            # Send MqttMessage event to core
            mqtt_msg = MqttMessage(topic=topic, payload_bytes=payload_bytes, ts=ts)
            actions = self.core.handle_event(mqtt_msg)
            self._execute_actions(actions)

        except Exception as e:
            logger.error("Error processing message: %s", e, exc_info=True)

    def publish_telemetry(self) -> None:
        """Generate and publish moisture telemetry reading via core layer."""
        moisture_value = self.moisture_sensor.get_reading()
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        # Send MetricSample event to core
        metric_sample = MetricSample(metric="moisture", value=moisture_value, ts=ts)
        actions = self.core.handle_event(metric_sample)
        self._execute_actions(actions)

        logger.info("Published telemetry: moisture=%.2f", moisture_value)

    def publish_status(self, online: bool = True) -> None:
        """Publish online/offline status via core layer."""
        ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if online:
            actions = self.core.handle_event(Tick(ts=ts))
        else:
            actions = self.core.shutdown(ts=ts)
        self._execute_actions(actions)
        logger.info("Published status: online=%s", online)

    def publish_command_ack(self, command: str, cmd_id: str) -> None:
        """
        Publish command acknowledgment.

        Note: This is now handled by core layer via CommandResult events.
        This method is kept for backward compatibility with tests.
        """
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
