
import json
from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from motherplant.management.commands import mqtt_client

class MqttClientTests(TestCase):
	def setUp(self):
		self.valid_topic = "planty/plant01/telemetry/temperature"
		self.invalid_topic = "invalid/plant01/telemetry/temperature"
		self.payload = {
			"value": 25.5,
			"ts": int(datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc).timestamp())
		}

	def test_parse_topic_valid(self):
		plant_id, metric = mqtt_client.parse_topic(self.valid_topic)
		self.assertEqual(plant_id, "plant01")
		self.assertEqual(metric, "temperature")

	def test_parse_topic_invalid(self):
		with self.assertRaises(ValueError):
			mqtt_client.parse_topic(self.invalid_topic)

	@patch("motherplant.management.commands.mqtt_client.Plant")
	@patch("motherplant.management.commands.mqtt_client.PlantState")
	@patch("motherplant.management.commands.mqtt_client.Telemetry")
	def test_on_message_valid(self, mock_telemetry, mock_plantstate, mock_plant):
		mock_msg = MagicMock()
		mock_msg.topic = self.valid_topic
		mock_msg.payload.decode.return_value = json.dumps(self.payload)

		mock_plant.objects.get.return_value = MagicMock()
		mock_plantstate.objects.get_or_create.return_value = (MagicMock(), True)

		mqtt_client.on_message(None, None, mock_msg)
		self.assertTrue(mock_telemetry.objects.create.called)
		self.assertTrue(mock_plantstate.objects.get_or_create.called)

	@patch("motherplant.management.commands.mqtt_client.logger")
	def test_on_message_invalid_json(self, mock_logger):
		mock_msg = MagicMock()
		mock_msg.topic = self.valid_topic
		mock_msg.payload.decode.return_value = "not a json"
		mqtt_client.on_message(None, None, mock_msg)
		self.assertTrue(mock_logger.warning.called)
