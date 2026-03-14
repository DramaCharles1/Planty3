from django.contrib import admin

from .models import CommandLog, Plant, PlantState, Telemetry


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


@admin.register(CommandLog)
class CommandLogAdmin(admin.ModelAdmin):
    list_display = ("plant", "command", "cmd_id", "sent_at", "ack_at", "ok")
    list_filter = ("command", "ok")
    search_fields = ("plant__plant_id", "cmd_id")
