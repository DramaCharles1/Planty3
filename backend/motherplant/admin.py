from django.contrib import admin
from .models import Plant, PlantState, Telemetry

@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("plant_id", "name", "location", "created_at")
    search_fields = ("plant_id", "name")

@admin.register(PlantState)
class PlantStateAdmin(admin.ModelAdmin):
    list_display = ("plant", "online", "last_seen")

@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ("plant", "type", "value", "timestamp")
    list_filter = ("type",)
