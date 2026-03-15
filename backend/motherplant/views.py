from datetime import timedelta

from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CommandLog, Plant, Telemetry
from .serializers import (
    CommandLogSerializer,
    PlantDetailSerializer,
    PlantListSerializer,
    PlantWriteSerializer,
    SendCommandSerializer,
    TelemetrySerializer,
)
from .services import send_command


class PlantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Plant model.

    list: Get all plants with their current state
    retrieve: Get a single plant by plant_id
    create: Create a new plant
    update: Update an existing plant
    partial_update: Partially update an existing plant
    destroy: Delete a plant and all related data
    telemetry: Get telemetry data for a plant (filterable by time range)
    commands: Get command history for a plant
    send_command: Send a command to a plant device
    """

    queryset = Plant.objects.select_related("state").all()
    lookup_field = "plant_id"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["plant_id", "name", "location"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PlantListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return PlantWriteSerializer
        return PlantDetailSerializer

    def perform_destroy(self, instance):
        """
        Delete plant and all related data (PlantState, Telemetry, CommandLog).
        Django's CASCADE handles this automatically.
        """
        instance.delete()
        # Related objects deleted via CASCADE: PlantState, Telemetry, CommandLog

    @action(detail=True, methods=["get"])
    def telemetry(self, request, plant_id=None):
        """Get telemetry data for a plant, optionally filtered by time range"""
        plant = self.get_object()
        queryset = Telemetry.objects.filter(plant=plant)

        # Filter by hours parameter (frontend sends this)
        hours = request.query_params.get("hours")
        if hours:
            try:
                hours_int = int(hours)
                queryset = queryset.filter(
                    timestamp__gte=timezone.now() - timedelta(hours=hours_int)
                )
            except (ValueError, TypeError):
                pass

        # Filter by time range if provided (explicit timestamps)
        from_time = request.query_params.get("from")
        to_time = request.query_params.get("to")

        if from_time:
            queryset = queryset.filter(timestamp__gte=from_time)
        if to_time:
            queryset = queryset.filter(timestamp__lte=to_time)

        # Filter by telemetry type (frontend sends "telemetry_type")
        telemetry_type = request.query_params.get("telemetry_type") or request.query_params.get(
            "type"
        )
        if telemetry_type:
            queryset = queryset.filter(type=telemetry_type)

        queryset = queryset.order_by("-timestamp")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TelemetrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TelemetrySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def commands(self, request, plant_id=None):
        """Get command history for a plant"""
        plant = self.get_object()
        queryset = CommandLog.objects.filter(plant=plant).order_by("-sent_at")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CommandLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CommandLogSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def send_command(self, request, plant_id=None):
        """Send a command to a plant device"""
        plant = self.get_object()

        serializer = SendCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        command = serializer.validated_data["command"]
        args = serializer.validated_data.get("args", {})

        try:
            command_log = send_command(plant, command, **args)
            return Response(
                CommandLogSerializer(command_log).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
