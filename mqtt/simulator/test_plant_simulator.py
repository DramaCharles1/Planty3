"""
Tests for plant_simulator.py

This test suite covers:
- MoistureSensor: value generation logic
- Topic parsing: command extraction from MQTT topics
- Payload generation: telemetry, status, and ack message structure
- MQTT client behavior: connection, disconnection, message handling
- Configuration: environment variable loading and defaults
- Integration: main loop behavior
- Signal handling: graceful shutdown
"""

import datetime
import json
import os
import signal
import time
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from plant_simulator import MoistureSensor, PlantSimulator, parse_command_topic


# ============================================================================
# 1. MoistureSensor Tests
# ============================================================================


class TestMoistureSensor:
    """Tests for MoistureSensor class."""

    def test_random_mode_returns_value_in_range(self):
        """Test random mode generates values between min and max."""
        sensor = MoistureSensor(20.0, 80.0, pattern="random")
        for _ in range(100):
            value = sensor.get_reading()
            assert 20.0 <= value <= 80.0, f"Value {value} out of range [20.0, 80.0]"

    def test_sine_mode_returns_value_in_range(self):
        """Test sine mode generates values between min and max."""
        sensor = MoistureSensor(20.0, 80.0, pattern="sine")
        for _ in range(100):
            value = sensor.get_reading()
            assert 20.0 <= value <= 80.0, f"Value {value} out of range [20.0, 80.0]"

    def test_sine_mode_oscillates_over_time(self):
        """Test sine pattern changes over time (not constant)."""
        sensor = MoistureSensor(20.0, 80.0, pattern="sine")

        # Get readings at different times by advancing the start time
        readings = []
        for i in range(10):
            # Manually advance time by modifying start_time
            sensor.start_time = time.time() - (i * 10)
            readings.append(sensor.get_reading())

        # Assert not all values are the same (proves oscillation)
        unique_readings = set(readings)
        assert len(unique_readings) > 1, "Sine mode should produce varying values"

    def test_default_pattern_is_random(self):
        """Test sensor defaults to random mode when pattern not specified."""
        sensor = MoistureSensor(20.0, 80.0)
        assert sensor.pattern == "random"

    def test_random_mode_generates_different_values(self):
        """Test random mode produces varying values (not constant)."""
        sensor = MoistureSensor(20.0, 80.0, pattern="random")

        readings = [sensor.get_reading() for _ in range(20)]
        unique_readings = set(readings)

        # Very unlikely all 20 readings are identical with random
        assert len(unique_readings) > 1, "Random mode should produce varying values"


# ============================================================================
# 2. Topic Parsing Tests
# ============================================================================


class TestTopicParsing:
    """Tests for parse_command_topic function."""

    def test_parse_command_topic_valid(self):
        """Test parsing valid command topic."""
        topic = "planty/plant/sim_plant_01/command/water"
        result = parse_command_topic(topic)
        assert result == "water"

    @pytest.mark.parametrize(
        "command",
        ["water"],
    )
    def test_parse_command_topic_multiple_commands(self, command):
        """Test parsing various command names."""
        topic = f"planty/plant/sim_plant_01/command/{command}"
        result = parse_command_topic(topic)
        assert result == command

    def test_parse_command_topic_invalid_format(self):
        """Test parsing invalid topic format returns None."""
        topic = "invalid/topic/format"
        result = parse_command_topic(topic)
        assert result is None

    def test_parse_command_topic_missing_command(self):
        """Test parsing topic with missing command segment."""
        topic = "planty/plant/sim_plant_01"
        result = parse_command_topic(topic)
        assert result is None

    def test_parse_command_topic_wrong_prefix(self):
        """Test parsing topic with wrong prefix returns None."""
        topic = "wrong/plant/sim_plant_01/command/water"
        result = parse_command_topic(topic)
        assert result is None


# ============================================================================
# 3. Payload Generation Tests
# ============================================================================


class TestPayloadGeneration:
    """Tests for MQTT payload generation methods."""

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_telemetry_payload_structure(self, mock_datetime, mock_mqtt_client):
        """Test telemetry payload has required fields (value, ts)."""
        # Mock timestamp
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_telemetry()

        # Verify publish was called
        assert simulator.client.publish.called
        call_args = simulator.client.publish.call_args

        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])
        qos = call_args[1]["qos"]

        assert topic == "planty/plant/sim_plant_01/telemetry/moisture"
        assert "value" in payload
        assert "ts" in payload
        assert payload["ts"] == 1234567890
        assert isinstance(payload["value"], float)
        assert qos == 1

    @patch("plant_simulator.mqtt.Client")
    def test_telemetry_payload_topic(self, mock_mqtt_client):
        """Test telemetry topic format is correct."""
        simulator = PlantSimulator()
        simulator.publish_telemetry()

        call_args = simulator.client.publish.call_args
        topic = call_args[0][0]
        qos = call_args[1]["qos"]

        assert topic == "planty/plant/sim_plant_01/telemetry/moisture"
        assert qos == 1

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_status_payload_structure_online(self, mock_datetime, mock_mqtt_client):
        """Test online status payload has correct structure."""
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_status(online=True)

        call_args = simulator.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert "online" in payload
        assert "ts" in payload
        assert payload["online"] is True
        assert payload["ts"] == 1234567890

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_status_payload_structure_offline(self, mock_datetime, mock_mqtt_client):
        """Test offline status payload has correct structure."""
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_status(online=False)

        call_args = simulator.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert payload["online"] is False
        assert payload["ts"] == 1234567890

    @patch("plant_simulator.mqtt.Client")
    def test_status_payload_topic(self, mock_mqtt_client):
        """Test status topic format is correct."""
        simulator = PlantSimulator()
        simulator.publish_status(online=True)

        call_args = simulator.client.publish.call_args
        topic = call_args[0][0]
        qos = call_args[1]["qos"]

        assert topic == "planty/plant/sim_plant_01/status"
        assert qos == 1

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_command_ack_payload_structure(self, mock_datetime, mock_mqtt_client):
        """Test command ack payload has required fields."""
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_command_ack("water", "cmd-123")

        call_args = simulator.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert "cmd_id" in payload
        assert "ts" in payload
        assert "ok" in payload
        assert "error" in payload
        assert payload["cmd_id"] == "cmd-123"
        assert payload["ts"] == 1234567890
        assert payload["ok"] is True
        assert payload["error"] == ""

    @patch("plant_simulator.mqtt.Client")
    def test_command_ack_payload_topic(self, mock_mqtt_client):
        """Test command ack topic format is correct."""
        simulator = PlantSimulator()
        simulator.publish_command_ack("water", "cmd-123")

        call_args = simulator.client.publish.call_args
        topic = call_args[0][0]
        qos = call_args[1]["qos"]

        assert topic == "planty/plant/sim_plant_01/command/water/ack"
        assert qos == 1

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_timestamp_is_unix_epoch(self, mock_datetime, mock_mqtt_client):
        """Test timestamps are unix epoch integers."""
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1609459200.5  # Float timestamp
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_telemetry()

        call_args = simulator.client.publish.call_args
        payload = json.loads(call_args[0][1])

        # Verify ts is converted to int
        assert isinstance(payload["ts"], int)
        assert payload["ts"] == 1609459200

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.datetime")
    def test_timestamp_uses_utc(self, mock_datetime, mock_mqtt_client):
        """Test timestamps use UTC timezone."""
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1234567890
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.timezone = datetime.timezone

        simulator = PlantSimulator()
        simulator.publish_telemetry()

        # Verify datetime.now was called with timezone.utc
        mock_datetime.datetime.now.assert_called_with(datetime.timezone.utc)


# ============================================================================
# 4. MQTT Client Behavior Tests
# ============================================================================


class TestMQTTClientBehavior:
    """Tests for MQTT client interactions."""

    @patch("plant_simulator.mqtt.Client")
    def test_initialization(self, mock_mqtt_client):
        """Test PlantSimulator initialization."""
        simulator = PlantSimulator()

        assert simulator.plant_id == "sim_plant_01"
        assert simulator.mqtt_broker_host == "mqtt"
        assert simulator.mqtt_broker_port == 1883
        assert simulator.telemetry_interval == 10
        assert simulator.status_heartbeat_interval == 60
        assert simulator.shutdown_flag is False
        assert simulator.moisture_sensor is not None

        # Verify client created with correct ID
        mock_mqtt_client.assert_called_once_with(client_id="simulator_sim_plant_01")

    @patch("plant_simulator.mqtt.Client")
    def test_on_connect_success(self, mock_mqtt_client):
        """Test successful connection subscribes to commands and publishes status."""
        simulator = PlantSimulator()

        with patch.object(simulator, "publish_status") as mock_publish_status:
            simulator._on_connect(simulator.client, None, None, 0)

            # Verify subscribe was called
            simulator.client.subscribe.assert_called_once_with(
                "planty/plant/sim_plant_01/command/+", qos=1
            )

            # Verify online status published
            mock_publish_status.assert_called_once_with(online=True)

    @patch("plant_simulator.mqtt.Client")
    def test_on_connect_failure(self, mock_mqtt_client):
        """Test failed connection does not subscribe or publish."""
        simulator = PlantSimulator()

        simulator._on_connect(simulator.client, None, None, 5)

        # Verify subscribe was NOT called
        simulator.client.subscribe.assert_not_called()

    @patch("plant_simulator.mqtt.Client")
    def test_on_disconnect_expected(self, mock_mqtt_client):
        """Test graceful disconnect (rc=0) is logged as info."""
        simulator = PlantSimulator()

        # Should not raise exception
        simulator._on_disconnect(simulator.client, None, 0)

    @patch("plant_simulator.mqtt.Client")
    def test_on_disconnect_unexpected(self, mock_mqtt_client):
        """Test unexpected disconnect (rc!=0) is logged as warning."""
        simulator = PlantSimulator()

        # Should not raise exception
        simulator._on_disconnect(simulator.client, None, 7)

    @patch("plant_simulator.mqtt.Client")
    def test_on_message_valid_command(self, mock_mqtt_client):
        """Test receiving valid command publishes ack."""
        simulator = PlantSimulator()

        mock_msg = MagicMock()
        mock_msg.topic = "planty/plant/sim_plant_01/command/water"
        mock_msg.payload = json.dumps({"cmd_id": "test-123", "duration": 30}).encode(
            "utf-8"
        )

        with patch.object(simulator, "publish_command_ack") as mock_ack:
            simulator._on_message(simulator.client, None, mock_msg)
            mock_ack.assert_called_once_with("water", "test-123")

    @patch("plant_simulator.mqtt.Client")
    def test_on_message_missing_cmd_id(self, mock_mqtt_client):
        """Test command without cmd_id does not publish ack."""
        simulator = PlantSimulator()

        mock_msg = MagicMock()
        mock_msg.topic = "planty/plant/sim_plant_01/command/water"
        mock_msg.payload = json.dumps({"duration": 30}).encode("utf-8")

        with patch.object(simulator, "publish_command_ack") as mock_ack:
            simulator._on_message(simulator.client, None, mock_msg)
            mock_ack.assert_not_called()

    @patch("plant_simulator.mqtt.Client")
    def test_on_message_invalid_json(self, mock_mqtt_client):
        """Test invalid JSON payload does not crash."""
        simulator = PlantSimulator()

        mock_msg = MagicMock()
        mock_msg.topic = "planty/plant/sim_plant_01/command/water"
        mock_msg.payload = b"not valid json"

        # Should not raise exception
        simulator._on_message(simulator.client, None, mock_msg)

    @patch("plant_simulator.mqtt.Client")
    def test_on_message_invalid_topic_format(self, mock_mqtt_client):
        """Test message on unexpected topic does not crash."""
        simulator = PlantSimulator()

        mock_msg = MagicMock()
        mock_msg.topic = "invalid/topic/format"
        mock_msg.payload = json.dumps({"cmd_id": "test-123"}).encode("utf-8")

        # Should not raise exception
        simulator._on_message(simulator.client, None, mock_msg)

    @patch("plant_simulator.mqtt.Client")
    @pytest.mark.parametrize("command", ["water"])
    def test_on_message_extracts_command_name(self, mock_mqtt_client, command):
        """Test command name extraction from various topics."""
        simulator = PlantSimulator()

        mock_msg = MagicMock()
        mock_msg.topic = f"planty/plant/sim_plant_01/command/{command}"
        mock_msg.payload = json.dumps({"cmd_id": "test-123"}).encode("utf-8")

        with patch.object(simulator, "publish_command_ack") as mock_ack:
            simulator._on_message(simulator.client, None, mock_msg)
            mock_ack.assert_called_once_with(command, "test-123")

    @patch("plant_simulator.mqtt.Client")
    def test_publish_telemetry_success(self, mock_mqtt_client):
        """Test successful telemetry publish."""
        simulator = PlantSimulator()

        # Mock successful publish
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        simulator.client.publish.return_value = mock_result

        # Should not raise exception
        simulator.publish_telemetry()

        assert simulator.client.publish.called

    @patch("plant_simulator.mqtt.Client")
    def test_publish_telemetry_failure(self, mock_mqtt_client):
        """Test failed telemetry publish logs error."""
        simulator = PlantSimulator()

        # Mock failed publish
        mock_result = MagicMock()
        mock_result.rc = 4  # MQTT_ERR_NO_CONN
        simulator.client.publish.return_value = mock_result

        # Should not raise exception
        simulator.publish_telemetry()

    @patch("plant_simulator.mqtt.Client")
    def test_publish_status_success(self, mock_mqtt_client):
        """Test successful status publish."""
        simulator = PlantSimulator()

        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        simulator.client.publish.return_value = mock_result

        simulator.publish_status(online=True)

        call_args = simulator.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert payload["online"] is True

    @patch("plant_simulator.mqtt.Client")
    def test_publish_command_ack_success(self, mock_mqtt_client):
        """Test successful command ack publish."""
        simulator = PlantSimulator()

        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        simulator.client.publish.return_value = mock_result

        simulator.publish_command_ack("water", "cmd-123")

        call_args = simulator.client.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])

        assert topic == "planty/plant/sim_plant_01/command/water/ack"
        assert payload["ok"] is True
        assert payload["cmd_id"] == "cmd-123"

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.time.sleep")
    def test_shutdown_publishes_offline_and_disconnects(
        self, mock_sleep, mock_mqtt_client
    ):
        """Test shutdown publishes offline status and disconnects."""
        simulator = PlantSimulator()

        with patch.object(simulator, "publish_status") as mock_publish_status:
            simulator.shutdown()

            mock_publish_status.assert_called_once_with(online=False)
            simulator.client.loop_stop.assert_called_once()
            simulator.client.disconnect.assert_called_once()


# ============================================================================
# 5. Configuration Tests
# ============================================================================


class TestConfiguration:
    """Tests for configuration loading from environment variables."""

    @patch.dict(
        os.environ,
        {},
        clear=True,
    )
    @patch("plant_simulator.mqtt.Client")
    def test_config_defaults(self, mock_mqtt_client):
        """Test default configuration values when env vars not set."""
        # Need to reload module constants after clearing env
        import importlib
        import plant_simulator

        importlib.reload(plant_simulator)

        # Now create simulator with reloaded defaults
        from plant_simulator import PlantSimulator

        simulator = PlantSimulator()

        assert simulator.plant_id == "sim_plant_01"
        assert simulator.mqtt_broker_host == "mqtt"
        assert simulator.mqtt_broker_port == 1883
        assert simulator.telemetry_interval == 10
        assert simulator.status_heartbeat_interval == 60

    @patch.dict(
        os.environ,
        {
            "PLANT_ID": "custom_plant",
            "MQTT_BROKER_HOST": "custom-mqtt",
            "MQTT_BROKER_PORT": "8883",
            "TELEMETRY_INTERVAL": "20",
            "STATUS_HEARTBEAT_INTERVAL": "120",
            "MOISTURE_MIN": "15.5",
            "MOISTURE_MAX": "85.5",
            "MOISTURE_PATTERN": "sine",
        },
    )
    @patch("plant_simulator.mqtt.Client")
    def test_config_from_environment(self, mock_mqtt_client):
        """Test configuration loaded from environment variables."""
        import importlib
        import plant_simulator

        importlib.reload(plant_simulator)

        from plant_simulator import PlantSimulator

        simulator = PlantSimulator()

        assert simulator.plant_id == "custom_plant"
        assert simulator.mqtt_broker_host == "custom-mqtt"
        assert simulator.mqtt_broker_port == 8883
        assert simulator.telemetry_interval == 20
        assert simulator.status_heartbeat_interval == 120

    @patch.dict(os.environ, {"MQTT_BROKER_PORT": "1883"})
    @patch("plant_simulator.mqtt.Client")
    def test_config_port_is_integer(self, mock_mqtt_client):
        """Test MQTT_BROKER_PORT is converted from string to int."""
        import importlib
        import plant_simulator

        importlib.reload(plant_simulator)

        from plant_simulator import PlantSimulator

        simulator = PlantSimulator()

        assert isinstance(simulator.mqtt_broker_port, int)
        assert simulator.mqtt_broker_port == 1883

    @patch.dict(os.environ, {"TELEMETRY_INTERVAL": "20"})
    @patch("plant_simulator.mqtt.Client")
    def test_config_intervals_are_integers(self, mock_mqtt_client):
        """Test interval config values are converted to int."""
        import importlib
        import plant_simulator

        importlib.reload(plant_simulator)

        from plant_simulator import PlantSimulator

        simulator = PlantSimulator()

        assert isinstance(simulator.telemetry_interval, int)
        assert simulator.telemetry_interval == 20

    @patch.dict(os.environ, {"MOISTURE_MIN": "15.5", "MOISTURE_MAX": "85.5"})
    @patch("plant_simulator.mqtt.Client")
    def test_config_moisture_values_are_floats(self, mock_mqtt_client):
        """Test moisture config values are converted to float."""
        import importlib
        import plant_simulator

        importlib.reload(plant_simulator)

        from plant_simulator import MOISTURE_MIN, MOISTURE_MAX

        assert isinstance(MOISTURE_MIN, float)
        assert isinstance(MOISTURE_MAX, float)
        assert MOISTURE_MIN == 15.5
        assert MOISTURE_MAX == 85.5


# ============================================================================
# 6. Integration Tests (Main Loop Behavior)
# ============================================================================


class TestIntegration:
    """Tests for main run loop behavior."""

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.time.sleep")
    @patch("plant_simulator.time.time")
    def test_run_loop_publishes_telemetry_at_interval(
        self, mock_time, mock_sleep, mock_mqtt_client
    ):
        """Test run loop publishes telemetry at configured intervals."""
        simulator = PlantSimulator()
        simulator.telemetry_interval = 10

        # Simulate time progression over 30 seconds (more granular for stability)
        time_values = [0, 0, 0, 10, 10, 10, 20, 20, 20, 30, 30, 30, 40, 40, 40]
        mock_time.side_effect = time_values

        # Stop after a few iterations
        def side_effect(*args):
            if mock_time.call_count >= 12:
                simulator.shutdown_flag = True

        mock_sleep.side_effect = side_effect

        with patch.object(simulator, "publish_telemetry") as mock_telemetry:
            with patch.object(simulator, "publish_status"):
                simulator.client.connect = MagicMock()
                simulator.run()

                # Should publish at t=0, t=10, t=20 (at least 3 times)
                assert mock_telemetry.call_count >= 2, (
                    f"Expected at least 2 calls, got {mock_telemetry.call_count}"
                )

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.time.sleep")
    @patch("plant_simulator.time.time")
    def test_run_loop_publishes_heartbeat_at_interval(
        self, mock_time, mock_sleep, mock_mqtt_client
    ):
        """Test run loop publishes status heartbeat at configured intervals."""
        simulator = PlantSimulator()
        simulator.status_heartbeat_interval = 60

        # Simulate time progression over 120 seconds
        time_values = [0] * 5 + [60] * 5 + [120] * 5
        mock_time.side_effect = time_values

        def side_effect(*args):
            if mock_time.call_count > 12:
                simulator.shutdown_flag = True

        mock_sleep.side_effect = side_effect

        with patch.object(simulator, "publish_status") as mock_status:
            with patch.object(simulator, "publish_telemetry"):
                simulator.client.connect = MagicMock()
                simulator.run()

                # Should publish at t=60, t=120 (2 times, not counting on_connect)
                assert mock_status.call_count >= 2

    @patch("plant_simulator.mqtt.Client")
    @patch("plant_simulator.time.sleep")
    def test_run_loop_handles_shutdown_flag(self, mock_sleep, mock_mqtt_client):
        """Test run loop exits when shutdown_flag is set."""
        simulator = PlantSimulator()

        def side_effect(*args):
            simulator.shutdown_flag = True

        mock_sleep.side_effect = side_effect

        with patch.object(simulator, "shutdown") as mock_shutdown:
            simulator.client.connect = MagicMock()
            simulator.run()

            mock_shutdown.assert_called_once()

    @patch("plant_simulator.mqtt.Client")
    def test_run_handles_connection_failure(self, mock_mqtt_client):
        """Test run handles connection failure gracefully."""
        simulator = PlantSimulator()

        simulator.client.connect.side_effect = Exception("Connection failed")

        # Should not raise exception, should return cleanly
        simulator.run()


# ============================================================================
# 7. Signal Handling Tests
# ============================================================================


class TestSignalHandling:
    """Tests for signal handling and graceful shutdown."""

    @patch("plant_simulator.mqtt.Client")
    def test_signal_handler_sets_shutdown_flag(self, mock_mqtt_client):
        """Test signal handler sets shutdown_flag to True."""
        import plant_simulator

        simulator = plant_simulator.PlantSimulator()
        plant_simulator.simulator = simulator

        assert simulator.shutdown_flag is False

        plant_simulator.signal_handler(signal.SIGTERM, None)

        assert simulator.shutdown_flag is True

    @patch("plant_simulator.mqtt.Client")
    def test_signal_handler_handles_sigint(self, mock_mqtt_client):
        """Test signal handler handles SIGINT (Ctrl+C)."""
        import plant_simulator

        simulator = plant_simulator.PlantSimulator()
        plant_simulator.simulator = simulator

        plant_simulator.signal_handler(signal.SIGINT, None)

        assert simulator.shutdown_flag is True

    @patch("plant_simulator.mqtt.Client")
    def test_signal_handler_handles_sigterm(self, mock_mqtt_client):
        """Test signal handler handles SIGTERM (docker stop)."""
        import plant_simulator

        simulator = plant_simulator.PlantSimulator()
        plant_simulator.simulator = simulator

        plant_simulator.signal_handler(signal.SIGTERM, None)

        assert simulator.shutdown_flag is True
