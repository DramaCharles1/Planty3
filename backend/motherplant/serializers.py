from rest_framework import serializers

from .models import CommandLog, Plant, PlantState, Telemetry


class PlantStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantState
        fields = ["online", "last_seen", "last_moisture", "updated_at"]


class PlantListSerializer(serializers.ModelSerializer):
    """Serializer for plant list view with nested state"""

    state = PlantStateSerializer(read_only=True)

    class Meta:
        model = Plant
        fields = ["id", "plant_id", "name", "location", "created_at", "state"]


class PlantDetailSerializer(serializers.ModelSerializer):
    """Serializer for plant detail view"""

    state = PlantStateSerializer(read_only=True)

    class Meta:
        model = Plant
        fields = ["id", "plant_id", "name", "location", "created_at", "state"]


class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetry
        fields = ["id", "type", "value", "timestamp", "received_at"]


class CommandLogSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = CommandLog
        fields = [
            "id",
            "command",
            "cmd_id",
            "sent_at",
            "ack_at",
            "ok",
            "error",
            "status",
            "created_at",
        ]

    def get_status(self, obj):
        """Derive command status from fields"""
        if obj.ack_at is None:
            return "pending"
        return "ok" if obj.ok else "error"


class SendCommandSerializer(serializers.Serializer):
    """Serializer for sending commands to plants"""

    command = serializers.CharField(
        max_length=64,
        help_text="Command name (e.g., water, calibrate, reset)",
    )
    args = serializers.DictField(
        required=False,
        default=dict,
        help_text="Optional command arguments as key-value pairs",
    )
