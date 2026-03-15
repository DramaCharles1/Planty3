import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TelemetryConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time telemetry updates.

    Clients connect to ws://localhost:8000/ws/plants/<plant_id>/telemetry/
    and receive telemetry updates as JSON messages.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.plant_id = self.scope["url_route"]["kwargs"]["plant_id"]
        self.room_group_name = f"telemetry_{self.plant_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()
        logger.info("WebSocket connected for plant: %s", self.plant_id)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info("WebSocket disconnected for plant: %s", self.plant_id)

    async def receive(self, text_data):
        """Handle messages from WebSocket (not used in current implementation)."""
        pass

    async def telemetry_update(self, event):
        """
        Receive telemetry update from room group and send to WebSocket.

        Event format:
        {
            "type": "telemetry_update",
            "plant_id": "sim_plant_01",
            "metric": "moisture",
            "value": 45.2,
            "timestamp": "2026-03-15T12:34:56Z"
        }
        """
        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "plant_id": event["plant_id"],
                    "metric": event["metric"],
                    "value": event["value"],
                    "timestamp": event["timestamp"],
                }
            )
        )
