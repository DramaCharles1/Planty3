"""Platform-agnostic core layer for plant MQTT behavior."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CoreConfig:
    """Core configuration shared across adapters."""

    plant_id: str
    allowed_commands: frozenset[str] = field(
        default_factory=lambda: frozenset({"water"})
    )

    def __post_init__(self) -> None:
        if not self.plant_id or not self.plant_id.strip():
            raise ValueError("plant_id is required")


@dataclass(frozen=True)
class Booted:
    ts: int


@dataclass(frozen=True)
class MqttConnected:
    ts: int


@dataclass(frozen=True)
class MqttDisconnected:
    ts: int


@dataclass(frozen=True)
class MqttMessage:
    topic: str
    payload_bytes: bytes
    ts: int


@dataclass(frozen=True)
class MetricSample:
    metric: str
    value: float
    ts: int


@dataclass(frozen=True)
class CommandResult:
    cmd_id: str
    command: str
    ok: bool
    error: str | None
    ts: int


@dataclass(frozen=True)
class Tick:
    ts: int


Event = (
    Booted
    | MqttConnected
    | MqttDisconnected
    | MqttMessage
    | MetricSample
    | CommandResult
    | Tick
)


@dataclass(frozen=True)
class Publish:
    topic: str
    payload_bytes: bytes
    qos: int
    retain: bool


@dataclass(frozen=True)
class ExecuteCommand:
    command: str
    args: dict[str, Any]
    cmd_id: str


@dataclass(frozen=True)
class Log:
    level: str
    message: str
    fields: dict[str, Any] = field(default_factory=dict)


Action = Publish | ExecuteCommand | Log


def build_telemetry_topic(plant_id: str, metric: str) -> str:
    return f"planty/plant/{plant_id}/telemetry/{metric}"


def build_status_topic(plant_id: str) -> str:
    return f"planty/plant/{plant_id}/status"


def build_command_ack_topic(plant_id: str, command: str) -> str:
    return f"planty/plant/{plant_id}/command/{command}/ack"


def parse_command_topic(topic: str) -> tuple[str, str] | None:
    """Parse command topic and return (plant_id, command) if valid."""
    parts = topic.split("/")
    if len(parts) != 5:
        return None
    if parts[0] != "planty" or parts[1] != "plant" or parts[3] != "command":
        return None
    command = parts[4]
    if not command:
        return None
    return parts[2], command


# Maximum size for ack cache to prevent unbounded memory growth
MAX_ACK_CACHE_SIZE = 1000


class CoreLayer:
    """Platform-agnostic core implementation for event/action contract."""

    def __init__(self, config: CoreConfig):
        self._config = config
        self._pending_commands: dict[str, str] = {}
        self._ack_cache: OrderedDict[str, Publish] = OrderedDict()

    def start(self) -> list[Action]:
        return []

    def shutdown(self, ts: int) -> list[Action]:
        return [self._build_status_action(False, ts)]

    def handle_event(self, event: Event) -> list[Action]:
        if isinstance(event, Booted):
            return [self._build_status_action(True, event.ts)]
        if isinstance(event, MqttConnected):
            return [self._build_log("info", "mqtt_connected")]
        if isinstance(event, MqttDisconnected):
            return [self._build_log("warning", "mqtt_disconnected")]
        if isinstance(event, MetricSample):
            return [self._build_telemetry_action(event.metric, event.value, event.ts)]
        if isinstance(event, CommandResult):
            return self._handle_command_result(event)
        if isinstance(event, MqttMessage):
            return self._handle_mqtt_message(event)
        if isinstance(event, Tick):
            return [self._build_status_action(True, event.ts)]
        return [
            self._build_log(
                "warning", "unknown_event", {"event_type": type(event).__name__}
            )
        ]

    def _build_log(
        self,
        level: str,
        message: str,
        fields: dict[str, Any] | None = None,
    ) -> Log:
        return Log(level=level, message=message, fields=fields or {})

    def _build_status_action(self, online: bool, ts: int) -> Publish:
        payload = {"online": online, "ts": ts}
        return Publish(
            topic=build_status_topic(self._config.plant_id),
            payload_bytes=json.dumps(payload).encode("utf-8"),
            qos=1,
            retain=True,
        )

    def _build_telemetry_action(self, metric: str, value: float, ts: int) -> Publish:
        payload = {"value": float(value), "ts": ts}
        return Publish(
            topic=build_telemetry_topic(self._config.plant_id, metric),
            payload_bytes=json.dumps(payload).encode("utf-8"),
            qos=0,
            retain=False,
        )

    def _handle_mqtt_message(self, event: MqttMessage) -> list[Action]:
        parsed = parse_command_topic(event.topic)
        if parsed is None:
            return [self._build_log("warning", "invalid_topic", {"topic": event.topic})]

        plant_id, command = parsed
        if plant_id != self._config.plant_id:
            return [
                self._build_log(
                    "warning",
                    "wrong_plant_id",
                    {
                        "topic_plant_id": plant_id,
                        "core_plant_id": self._config.plant_id,
                    },
                )
            ]

        try:
            payload_obj = json.loads(event.payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return [self._build_log("warning", "invalid_json", {"topic": event.topic})]

        if not isinstance(payload_obj, dict):
            return [
                self._build_log(
                    "warning", "invalid_payload_type", {"topic": event.topic}
                )
            ]

        cmd_id = payload_obj.get("cmd_id")
        ts = payload_obj.get("ts")
        if not isinstance(cmd_id, str) or not isinstance(ts, int):
            return [
                self._build_log(
                    "warning",
                    "missing_or_invalid_command_fields",
                    {"cmd_id": cmd_id, "ts": ts},
                )
            ]

        if (
            self._config.allowed_commands
            and command not in self._config.allowed_commands
        ):
            return [self._build_log("warning", "unknown_command", {"command": command})]

        cached_ack = self._ack_cache.get(cmd_id)
        if cached_ack is not None:
            # Move to end for LRU behavior
            self._ack_cache.move_to_end(cmd_id)
            return [cached_ack]

        if cmd_id in self._pending_commands:
            return [
                self._build_log("info", "duplicate_command_pending", {"cmd_id": cmd_id})
            ]

        args = {k: v for k, v in payload_obj.items() if k not in {"cmd_id", "ts"}}
        self._pending_commands[cmd_id] = command
        return [ExecuteCommand(command=command, args=args, cmd_id=cmd_id)]

    def _handle_command_result(self, event: CommandResult) -> list[Action]:
        if not event.cmd_id:
            return [
                self._build_log(
                    "warning", "invalid_command_result", {"reason": "empty_cmd_id"}
                )
            ]

        error_value: str | None = (
            None if event.ok else (event.error or "command_failed")
        )
        payload = {
            "cmd_id": event.cmd_id,
            "ts": event.ts,
            "ok": event.ok,
            "error": error_value,
        }
        publish_action = Publish(
            topic=build_command_ack_topic(self._config.plant_id, event.command),
            payload_bytes=json.dumps(payload).encode("utf-8"),
            qos=1,
            retain=False,
        )
        # Add to cache and move to end
        self._ack_cache[event.cmd_id] = publish_action
        self._ack_cache.move_to_end(event.cmd_id)
        # Evict oldest entry if cache exceeds max size
        if len(self._ack_cache) > MAX_ACK_CACHE_SIZE:
            self._ack_cache.popitem(last=False)
        self._pending_commands.pop(event.cmd_id, None)
        return [publish_action]
