import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APITestCase

from motherplant.management.commands import mqtt_client
from motherplant.models import Plant, PlantState, Telemetry


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

    @patch("motherplant.management.commands.mqtt_client.get_channel_layer")
    @patch("motherplant.management.commands.mqtt_client.Plant")
    @patch("motherplant.management.commands.mqtt_client.PlantState")
    @patch("motherplant.management.commands.mqtt_client.Telemetry")
    def test_on_message_valid_telemetry(
        self, mock_telemetry, mock_plantstate, mock_plant, mock_channel_layer
    ):
        mock_msg = MagicMock()
        mock_msg.topic = self.valid_telemetry_topic
        mock_msg.payload.decode.return_value = json.dumps(self.telemetry_payload)

        mock_plant_instance = MagicMock()
        mock_plant_instance.plant_id = "plant01"
        mock_plant.objects.get.return_value = mock_plant_instance
        mock_plantstate.objects.get_or_create.return_value = (MagicMock(), True)

        # Mock channel layer to return None (no broadcasting in tests)
        mock_channel_layer.return_value = None

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


class PlantCRUDTests(APITestCase):
    """Tests for Plant CRUD operations via API"""

    def setUp(self):
        self.plant_data = {
            "plant_id": "test_plant_01",
            "name": "Test Plant",
            "location": "Test Location",
        }
        self.plant = Plant.objects.create(**self.plant_data)

    def test_list_plants(self):
        """Test GET /api/plants/"""
        response = self.client.get("/api/plants/")
        self.assertEqual(response.status_code, 200)
        # API returns paginated results (or list depending on config)
        # Check for our test plant in the results
        if isinstance(response.data, dict):
            # Paginated response
            results = response.data.get("results", [])
        else:
            # List response
            results = response.data
        plant_ids = [p["plant_id"] for p in results]
        self.assertIn("test_plant_01", plant_ids)

    def test_retrieve_plant(self):
        """Test GET /api/plants/{plant_id}/"""
        response = self.client.get(f"/api/plants/{self.plant.plant_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plant_id"], "test_plant_01")
        self.assertEqual(response.data["name"], "Test Plant")

    def test_create_plant(self):
        """Test POST /api/plants/"""
        new_plant_data = {
            "plant_id": "new_plant_01",
            "name": "New Plant",
            "location": "New Location",
        }
        response = self.client.post("/api/plants/", new_plant_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["plant_id"], "new_plant_01")
        self.assertEqual(response.data["name"], "New Plant")

        # Verify plant exists in database
        plant = Plant.objects.get(plant_id="new_plant_01")
        self.assertEqual(plant.name, "New Plant")
        self.assertEqual(plant.location, "New Location")

    def test_create_plant_duplicate_plant_id(self):
        """Test creating plant with duplicate plant_id fails"""
        duplicate_data = {
            "plant_id": "test_plant_01",
            "name": "Duplicate",
        }
        response = self.client.post("/api/plants/", duplicate_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_plant_empty_plant_id(self):
        """Test creating plant with empty plant_id fails"""
        invalid_data = {
            "plant_id": "",
            "name": "Invalid",
        }
        response = self.client.post("/api/plants/", invalid_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_plant_missing_plant_id(self):
        """Test creating plant without plant_id fails"""
        invalid_data = {
            "name": "Invalid",
        }
        response = self.client.post("/api/plants/", invalid_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_plant(self):
        """Test PUT /api/plants/{plant_id}/"""
        update_data = {
            "plant_id": "test_plant_01",
            "name": "Updated Plant",
            "location": "Updated Location",
        }
        response = self.client.put(
            f"/api/plants/{self.plant.plant_id}/", update_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Plant")
        self.assertEqual(response.data["location"], "Updated Location")

        # Verify plant updated in database
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, "Updated Plant")
        self.assertEqual(self.plant.location, "Updated Location")

    def test_partial_update_plant(self):
        """Test PATCH /api/plants/{plant_id}/"""
        update_data = {
            "name": "Partially Updated",
        }
        response = self.client.patch(
            f"/api/plants/{self.plant.plant_id}/", update_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Partially Updated")
        self.assertEqual(response.data["location"], "Test Location")  # Unchanged

    def test_delete_plant(self):
        """Test DELETE /api/plants/{plant_id}/"""
        # Create related data to verify cascade delete
        PlantState.objects.create(plant=self.plant)
        Telemetry.objects.create(
            plant=self.plant,
            type="moisture",
            value=50.0,
            timestamp=datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc),
        )

        response = self.client.delete(f"/api/plants/{self.plant.plant_id}/")
        self.assertEqual(response.status_code, 204)

        # Verify plant deleted
        self.assertFalse(Plant.objects.filter(plant_id="test_plant_01").exists())

        # Verify related data deleted (cascade)
        self.assertFalse(PlantState.objects.filter(plant=self.plant.id).exists())
        self.assertFalse(Telemetry.objects.filter(plant=self.plant.id).exists())

    def test_delete_nonexistent_plant(self):
        """Test deleting non-existent plant returns 404"""
        response = self.client.delete("/api/plants/nonexistent_plant/")
        self.assertEqual(response.status_code, 404)
