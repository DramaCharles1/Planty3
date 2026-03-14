import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase

from motherplant.management.commands import mqtt_client


class MqttClientTests(TestCase):
    def setUp(self):
        self.valid_telemetry_topic = "planty/plant/plant01/telemetry/moisture"
        self.valid_status_topic = "planty/plant/plant01/status"
        self.valid_command_topic = "planty/plant/plant01/command/water"
        self.valid_command_ack_topic = "planty/plant/plant01/command/water/ack"
        self.invalid_topic = "invalid/plant/plant01/telemetry/moisture"
        self.telemetry_payload = {
            "value": 25.5,
            "ts": int(datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
        }
        self.status_payload = {
            "online": True,
            "ts": int(datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
        }
        self.command_ack_payload = {
            "cmd_id": "test-cmd-123",
            "ts": int(datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
            "ok": True,
            "error": "",
        }

    def test_parse_topic_valid_telemetry(self):
        plant_id, category, subcategory, metric = mqtt_client.parse_topic(
            self.valid_telemetry_topic
        )
        self.assertEqual(plant_id, "plant01")
        self.assertEqual(category, "telemetry")
        self.assertIsNone(subcategory)
        self.assertEqual(metric, "moisture")

    def test_parse_topic_valid_status(self):
        plant_id, category, subcategory, metric = mqtt_client.parse_topic(self.valid_status_topic)
        self.assertEqual(plant_id, "plant01")
        self.assertEqual(category, "status")
        self.assertIsNone(subcategory)
        self.assertIsNone(metric)

    def test_parse_topic_valid_command(self):
        plant_id, category, subcategory, command = mqtt_client.parse_topic(self.valid_command_topic)
        self.assertEqual(plant_id, "plant01")
        self.assertEqual(category, "command")
        self.assertIsNone(subcategory)
        self.assertEqual(command, "water")

    def test_parse_topic_valid_command_ack(self):
        plant_id, category, subcategory, command = mqtt_client.parse_topic(
            self.valid_command_ack_topic
        )
        self.assertEqual(plant_id, "plant01")
        self.assertEqual(category, "command")
        self.assertEqual(subcategory, "ack")
        self.assertEqual(command, "water")

    def test_parse_topic_invalid(self):
        with self.assertRaises(ValueError):
            mqtt_client.parse_topic(self.invalid_topic)

    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.PlantState")
    @patch("motherplant.management.commands.mqtt_client.Telemetry")
    def test_on_message_valid_telemetry(self, mock_telemetry, mock_plantstate, mock_plant):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_telemetry_topic
        mock_msg.payload.decode.return_value = json.dumps(self.telemetry_payload)

        mock_plant.objects.get.return_value = MagicMock()
        mock_plantstate.objects.get_or_create.return_value = (MagicMock(), True)

        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_telemetry.objects.create.called)
        self.assertTrue(mock_plantstate.objects.get_or_create.called)

    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.PlantState")
    def test_on_message_valid_status(self, mock_plantstate, mock_plant):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_status_topic
        mock_msg.payload.decode.return_value = json.dumps(self.status_payload)

        mock_plant_instance = MagicMock()
        mock_plant_instance.plant_id = "plant01"
        mock_plant.objects.get.return_value = mock_plant_instance

        mock_state = MagicMock()
        mock_plantstate.objects.get_or_create.return_value = (mock_state, True)

        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_plantstate.objects.get_or_create.called)
        self.assertTrue(mock_state.save.called)

    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.CommandLog")
    def test_on_message_valid_command_ack(self, mock_commandlog, mock_plant):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_command_ack_topic
        mock_msg.payload.decode.return_value = json.dumps(self.command_ack_payload)

        mock_plant_instance = MagicMock()
        mock_plant_instance.plant_id = "plant01"
        mock_plant.objects.get.return_value = mock_plant_instance

        mock_cmd = MagicMock()
        mock_commandlog.objects.get.return_value = mock_cmd

        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_commandlog.objects.get.called)
        self.assertTrue(mock_cmd.save.called)
        self.assertEqual(mock_cmd.ok, True)

    @patch("motherplant.management.commands.mqtt_client.logger")
    def test_on_message_invalid_json(self, mock_logger):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_telemetry_topic
        mock_msg.payload.decode.return_value = "not a json"
        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_logger.warning.called)

    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.logger")
    def test_on_message_unknown_plant(self, mock_logger, mock_plant):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_status_topic
        mock_msg.payload.decode.return_value = json.dumps(self.status_payload)

        # Create a proper DoesNotExist exception class
        class DoesNotExist(Exception):
            pass

        mock_plant.DoesNotExist = DoesNotExist
        mock_plant.objects.get.side_effect = DoesNotExist
        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_logger.warning.called)

    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.CommandLog")
    @patch("motherplant.management.commands.mqtt_client.logger")
    def test_on_message_command_ack_unknown_command(self, mock_logger, mock_commandlog, mock_plant):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_command_ack_topic
        mock_msg.payload.decode.return_value = json.dumps(self.command_ack_payload)

        mock_plant_instance = MagicMock()
        mock_plant_instance.plant_id = "plant01"
        mock_plant.objects.get.return_value = mock_plant_instance

        # Create a proper DoesNotExist exception class
        class DoesNotExist(Exception):
            pass

        mock_commandlog.DoesNotExist = DoesNotExist
        mock_commandlog.objects.get.side_effect = DoesNotExist

        mqtt_client.on_message(None, None, mock_msg)
        self.assertTrue(mock_logger.warning.called)

    @patch("motherplant.management.commands.mqtt_client.CommandLog")
    @patch("motherplant.management.commands.mqtt_client.mqtt")
    def test_publish_command(self, mock_mqtt, mock_commandlog):
        mock_client = MagicMock()
        mock_plant = MagicMock()
        mock_plant.plant_id = "plant01"

        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mock_client.publish.return_value = mock_result

        result = mqtt_client.publish_command(
            mock_client, mock_plant, "water", "test-cmd-123", duration=30
        )

        self.assertTrue(mock_commandlog.objects.create.called)
        self.assertTrue(mock_client.publish.called)
        self.assertEqual(result.rc, 0)

        # Verify the topic format
        call_args = mock_client.publish.call_args
        self.assertEqual(call_args[0][0], "planty/plant/plant01/command/water")

        # Verify payload structure
        payload = json.loads(call_args[0][1])
        self.assertEqual(payload["cmd_id"], "test-cmd-123")
        self.assertIn("ts", payload)
        self.assertEqual(payload["duration"], 30)
