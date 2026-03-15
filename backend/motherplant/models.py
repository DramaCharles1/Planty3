from django.db import models


class Plant(models.Model):
    plant_id = models.CharField(
        max_length=64, unique=True, help_text="Unique device ID, e.g. plant01"
    )
    name = models.CharField(max_length=128, blank=True, help_text="Human-friendly name")
    location = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.plant_id


class PlantState(models.Model):
    plant = models.OneToOneField(Plant, on_delete=models.CASCADE, related_name="state")

    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    last_moisture = models.FloatField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"State of {self.plant.plant_id}"


class Telemetry(models.Model):
    TELEMETRY_TYPES = (("moisture", "Moisture"),)

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="telemetry")

    type = models.CharField(max_length=32, choices=TELEMETRY_TYPES)

    value = models.FloatField()

    timestamp = models.DateTimeField(help_text="Timestamp from device")

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["plant", "type", "timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.plant.plant_id} {self.type}={self.value}"


class CommandLog(models.Model):
    """
    Tracks commands sent to devices and their acknowledgments.
    """

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="commands")

    command = models.CharField(max_length=64, help_text="Command name (e.g., water)")

    cmd_id = models.CharField(max_length=128, help_text="Unique command ID (UUID or int)")

    sent_at = models.DateTimeField(help_text="When command was sent")

    ack_at = models.DateTimeField(null=True, blank=True, help_text="When ack was received")

    ok = models.BooleanField(null=True, blank=True, help_text="Ack success status")

    error = models.TextField(blank=True, help_text="Error message from ack if failed")

    raw_payload = models.JSONField(
        null=True, blank=True, help_text="Raw command payload for debugging"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["plant", "cmd_id"]),
            models.Index(fields=["plant", "sent_at"]),
        ]
        ordering = ["-sent_at"]

    def __str__(self):
        status = "pending"
        if self.ack_at:
            status = "ok" if self.ok else "error"
        return f"{self.plant.plant_id} {self.command} [{status}]"
