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


class PlantWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating plants"""

    class Meta:
        model = Plant
        fields = ["plant_id", "name", "location"]
        extra_kwargs = {
            "plant_id": {"required": True},
            "name": {"required": False, "allow_blank": True},
            "location": {"required": False, "allow_blank": True},
        }

    def validate_plant_id(self, value):
        """Ensure plant_id is not empty and meets basic constraints"""
        if not value or not value.strip():
            raise serializers.ValidationError("plant_id cannot be empty")
        if len(value) > 64:
            raise serializers.ValidationError("plant_id cannot exceed 64 characters")
        return value.strip()


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
