from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/plants/(?P<plant_id>[^/]+)/telemetry/$", consumers.TelemetryConsumer.as_asgi()),
]
