from django.db import models

class Plant(models.Model):
    plant_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="Unique device ID, e.g. plant01"
    )
    name = models.CharField(
        max_length=128,
        blank=True,
        help_text="Human-friendly name"
    )
    location = models.CharField(
        max_length=128,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.plant_id

class PlantState(models.Model):
    plant = models.OneToOneField(
        Plant,
        on_delete=models.CASCADE,
        related_name="state"
    )

    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    last_moisture = models.FloatField(null=True, blank=True)
    last_temperature = models.FloatField(null=True, blank=True)
    battery_level = models.FloatField(null=True, blank=True) # remove and migrate

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"State of {self.plant.plant_id}"

class Telemetry(models.Model):
    TELEMETRY_TYPES = (
        ("moisture", "Soil moisture"),
        ("temperature", "Temperature"),
    )

    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name="telemetry"
    )

    type = models.CharField(
        max_length=32,
        choices=TELEMETRY_TYPES
    )

    value = models.FloatField()

    timestamp = models.DateTimeField(
        help_text="Timestamp from device"
    )

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["plant", "type", "timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.plant.plant_id} {self.type}={self.value}"
