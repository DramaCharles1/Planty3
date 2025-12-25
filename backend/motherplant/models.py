from django.db import models


class Temperature(models.Model):
	value = models.FloatField(help_text="Temperature value (0–100)")
	unit = models.CharField(max_length=10, help_text="Unit, e.g. '%', 'C', 'F'")
	ts = models.BigIntegerField(help_text="Unix timestamp (seconds)")

	def __str__(self):
		return f"{self.value}{self.unit} at {self.ts}"
