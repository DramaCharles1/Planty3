"""Unit tests for core_layer event/action contract."""

from __future__ import annotations

import json

import pytest

from core_layer import (
    Booted,
    CommandResult,
    CoreConfig,
    CoreLayer,
    ExecuteCommand,
    Log,
    MetricSample,
    MqttConnected,
    MqttDisconnected,
    MqttMessage,
    Publish,
    build_command_ack_topic,
    build_status_topic,
    build_telemetry_topic,
    parse_command_topic,
)


def _decode_publish_payload(action: Publish) -> dict:
    return json.loads(action.payload_bytes.decode("utf-8"))


def test_config_requires_plant_id() -> None:
    with pytest.raises(ValueError, match="plant_id is required"):
        CoreConfig(plant_id="")


def test_start_returns_empty_actions() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))
    assert core.start() == []


def test_boot_event_emits_online_status_publish() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(Booted(ts=1700000000))

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, Publish)
    assert action.topic == build_status_topic("sim_plant_01")
    assert action.qos == 1
    assert action.retain is True
    assert _decode_publish_payload(action) == {"online": True, "ts": 1700000000}


def test_shutdown_emits_offline_status_publish() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.shutdown(ts=1700000001)

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, Publish)
    assert action.topic == build_status_topic("sim_plant_01")
    assert action.qos == 1
    assert action.retain is True
    assert _decode_publish_payload(action) == {"online": False, "ts": 1700000001}


def test_build_telemetry_topic() -> None:
    assert (
        build_telemetry_topic("sim_plant_01", "moisture")
        == "planty/plant/sim_plant_01/telemetry/moisture"
    )


def test_build_status_topic() -> None:
    assert build_status_topic("sim_plant_01") == "planty/plant/sim_plant_01/status"


def test_build_command_ack_topic() -> None:
    assert (
        build_command_ack_topic("sim_plant_01", "water")
        == "planty/plant/sim_plant_01/command/water/ack"
    )


def test_parse_command_topic_valid() -> None:
    assert parse_command_topic("planty/plant/sim_plant_01/command/water") == (
        "sim_plant_01",
        "water",
    )


@pytest.mark.parametrize(
    "topic",
    [
        "planty/plant/sim_plant_01/command",
        "planty/plant/sim_plant_01/status",
        "planty/plant/sim_plant_01/command/water/ack",
        "wrong/plant/sim_plant_01/command/water",
        "planty/device/sim_plant_01/command/water",
    ],
)
def test_parse_command_topic_invalid(topic: str) -> None:
    assert parse_command_topic(topic) is None


def test_metric_sample_emits_telemetry_publish_defaults() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(
        MetricSample(metric="moisture", value=42.5, ts=1700000002)
    )

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, Publish)
    assert action.topic == build_telemetry_topic("sim_plant_01", "moisture")
    assert action.qos == 0
    assert action.retain is False
    assert _decode_publish_payload(action) == {"value": 42.5, "ts": 1700000002}


def test_mqtt_connected_disconnected_emit_log_actions() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    connected_actions = core.handle_event(MqttConnected(ts=1700000003))
    disconnected_actions = core.handle_event(MqttDisconnected(ts=1700000004))

    assert isinstance(connected_actions[0], Log)
    assert connected_actions[0].level == "info"
    assert connected_actions[0].message == "mqtt_connected"

    assert isinstance(disconnected_actions[0], Log)
    assert disconnected_actions[0].level == "warning"
    assert disconnected_actions[0].message == "mqtt_disconnected"


def test_valid_command_message_emits_execute_command_action() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))
    payload = json.dumps({"cmd_id": "cmd-123", "ts": 1700000005, "duration": 3}).encode(
        "utf-8"
    )

    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000005,
        )
    )

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, ExecuteCommand)
    assert action.command == "water"
    assert action.cmd_id == "cmd-123"
    assert action.args == {"duration": 3}


@pytest.mark.parametrize(
    ("payload_bytes", "message"),
    [
        (b"not-json", "invalid_json"),
        (json.dumps([1, 2, 3]).encode("utf-8"), "invalid_payload_type"),
        (json.dumps({"ts": 1}).encode("utf-8"), "missing_or_invalid_command_fields"),
        (
            json.dumps({"cmd_id": "cmd-1", "ts": "bad-ts"}).encode("utf-8"),
            "missing_or_invalid_command_fields",
        ),
    ],
)
def test_invalid_payloads_emit_log_no_execute(
    payload_bytes: bytes, message: str
) -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_bytes,
            ts=1700000006,
        )
    )

    assert len(actions) == 1
    assert isinstance(actions[0], Log)
    assert actions[0].message == message


def test_invalid_topic_shape_emits_log() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/status",
            payload_bytes=json.dumps({"cmd_id": "x", "ts": 1}).encode("utf-8"),
            ts=1700000007,
        )
    )

    assert len(actions) == 1
    assert isinstance(actions[0], Log)
    assert actions[0].message == "invalid_topic"


def test_wrong_plant_id_emits_log() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))
    payload = json.dumps({"cmd_id": "cmd-123", "ts": 1700000008}).encode("utf-8")

    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/other_plant/command/water",
            payload_bytes=payload,
            ts=1700000008,
        )
    )

    assert len(actions) == 1
    assert isinstance(actions[0], Log)
    assert actions[0].message == "wrong_plant_id"


def test_unknown_command_emits_log_no_execute() -> None:
    core = CoreLayer(
        CoreConfig(plant_id="sim_plant_01", allowed_commands=frozenset({"water"}))
    )
    payload = json.dumps({"cmd_id": "cmd-123", "ts": 1700000009}).encode("utf-8")

    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/invalid",
            payload_bytes=payload,
            ts=1700000009,
        )
    )

    assert len(actions) == 1
    assert isinstance(actions[0], Log)
    assert actions[0].message == "unknown_command"


def test_command_result_ok_emits_ack_publish() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(
        CommandResult(
            cmd_id="cmd-200",
            command="water",
            ok=True,
            error=None,
            ts=1700000010,
        )
    )

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, Publish)
    assert action.topic == build_command_ack_topic("sim_plant_01", "water")
    assert action.qos == 1
    assert action.retain is False
    assert _decode_publish_payload(action) == {
        "cmd_id": "cmd-200",
        "ts": 1700000010,
        "ok": True,
        "error": None,
    }


def test_command_result_failure_emits_ack_with_error_string() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    actions = core.handle_event(
        CommandResult(
            cmd_id="cmd-201",
            command="water",
            ok=False,
            error="pump_jam",
            ts=1700000011,
        )
    )

    assert len(actions) == 1
    action = actions[0]
    assert isinstance(action, Publish)
    assert _decode_publish_payload(action) == {
        "cmd_id": "cmd-201",
        "ts": 1700000011,
        "ok": False,
        "error": "pump_jam",
    }


def test_duplicate_command_does_not_reexecute_and_reemits_cached_ack() -> None:
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))
    payload = json.dumps({"cmd_id": "cmd-300", "ts": 1700000012, "duration": 2}).encode(
        "utf-8"
    )

    first_actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000012,
        )
    )
    assert len(first_actions) == 1
    assert isinstance(first_actions[0], ExecuteCommand)

    pending_duplicate = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000013,
        )
    )
    assert len(pending_duplicate) == 1
    assert isinstance(pending_duplicate[0], Log)
    assert pending_duplicate[0].message == "duplicate_command_pending"

    result_actions = core.handle_event(
        CommandResult(
            cmd_id="cmd-300",
            command="water",
            ok=True,
            error=None,
            ts=1700000014,
        )
    )
    assert len(result_actions) == 1
    assert isinstance(result_actions[0], Publish)

    duplicate_after_ack = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000015,
        )
    )
    assert len(duplicate_after_ack) == 1
    assert isinstance(duplicate_after_ack[0], Publish)
    assert duplicate_after_ack[0] == result_actions[0]


def test_ack_cache_bounded_after_many_unique_cmd_ids() -> None:
    """Test ack cache does not grow unbounded - evicts oldest entries."""
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    # Fill cache beyond max size (MAX_ACK_CACHE_SIZE = 1000)
    # Send 1050 unique commands and ack them all
    for i in range(1050):
        cmd_id = f"cmd-{i:04d}"
        payload = json.dumps({"cmd_id": cmd_id, "ts": 1700000000 + i}).encode("utf-8")

        # Send command
        core.handle_event(
            MqttMessage(
                topic="planty/plant/sim_plant_01/command/water",
                payload_bytes=payload,
                ts=1700000000 + i,
            )
        )

        # Send ack
        core.handle_event(
            CommandResult(
                cmd_id=cmd_id,
                command="water",
                ok=True,
                error=None,
                ts=1700000000 + i,
            )
        )

    # Verify cache size is bounded to MAX_ACK_CACHE_SIZE (1000)
    assert len(core._ack_cache) == 1000


def test_recently_used_cache_entries_retained() -> None:
    """Test LRU behavior - recently accessed entries are retained."""
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    # Add 1000 commands to fill cache
    for i in range(1000):
        cmd_id = f"cmd-{i:04d}"
        payload = json.dumps({"cmd_id": cmd_id, "ts": 1700000000 + i}).encode("utf-8")

        core.handle_event(
            MqttMessage(
                topic="planty/plant/sim_plant_01/command/water",
                payload_bytes=payload,
                ts=1700000000 + i,
            )
        )

        core.handle_event(
            CommandResult(
                cmd_id=cmd_id,
                command="water",
                ok=True,
                error=None,
                ts=1700000000 + i,
            )
        )

    # Access an old entry (cmd-0050) to move it to end
    payload_old = json.dumps({"cmd_id": "cmd-0050", "ts": 1700001000}).encode("utf-8")
    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_old,
            ts=1700001000,
        )
    )
    # Should return cached ack (Publish action)
    assert len(actions) == 1
    assert isinstance(actions[0], Publish)

    # Add one more command to trigger eviction
    payload_new = json.dumps({"cmd_id": "cmd-1000", "ts": 1700001001}).encode("utf-8")
    core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_new,
            ts=1700001001,
        )
    )
    core.handle_event(
        CommandResult(
            cmd_id="cmd-1000",
            command="water",
            ok=True,
            error=None,
            ts=1700001001,
        )
    )

    # cmd-0050 should still be in cache (was moved to end)
    payload_check = json.dumps({"cmd_id": "cmd-0050", "ts": 1700001002}).encode("utf-8")
    actions_check = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_check,
            ts=1700001002,
        )
    )
    assert len(actions_check) == 1
    assert isinstance(actions_check[0], Publish)


def test_duplicate_within_cache_still_reemits_ack() -> None:
    """Test cache hit behavior - duplicate cmd_id returns cached ack."""
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    cmd_id = "cmd-test"
    payload = json.dumps({"cmd_id": cmd_id, "ts": 1700000000}).encode("utf-8")

    # Send command
    core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000000,
        )
    )

    # Send ack
    ack_actions = core.handle_event(
        CommandResult(
            cmd_id=cmd_id,
            command="water",
            ok=True,
            error=None,
            ts=1700000001,
        )
    )
    assert len(ack_actions) == 1
    original_ack = ack_actions[0]

    # Send duplicate command
    duplicate_actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload,
            ts=1700000002,
        )
    )

    # Should return same cached ack
    assert len(duplicate_actions) == 1
    assert isinstance(duplicate_actions[0], Publish)
    assert duplicate_actions[0] == original_ack


def test_evicted_old_cmd_id_no_longer_hits_cache() -> None:
    """Test cache miss after eviction - old cmd_id treated as new command."""
    core = CoreLayer(CoreConfig(plant_id="sim_plant_01"))

    # Add first command
    payload_first = json.dumps({"cmd_id": "cmd-0000", "ts": 1700000000}).encode("utf-8")
    core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_first,
            ts=1700000000,
        )
    )
    core.handle_event(
        CommandResult(
            cmd_id="cmd-0000",
            command="water",
            ok=True,
            error=None,
            ts=1700000000,
        )
    )

    # Fill cache with 1000 more commands to evict cmd-0000
    for i in range(1, 1001):
        cmd_id = f"cmd-{i:04d}"
        payload = json.dumps({"cmd_id": cmd_id, "ts": 1700000000 + i}).encode("utf-8")

        core.handle_event(
            MqttMessage(
                topic="planty/plant/sim_plant_01/command/water",
                payload_bytes=payload,
                ts=1700000000 + i,
            )
        )

        core.handle_event(
            CommandResult(
                cmd_id=cmd_id,
                command="water",
                ok=True,
                error=None,
                ts=1700000000 + i,
            )
        )

    # cmd-0000 should be evicted, verify it's not in cache
    assert "cmd-0000" not in core._ack_cache

    # Resend cmd-0000 - should be treated as new command (ExecuteCommand)
    actions = core.handle_event(
        MqttMessage(
            topic="planty/plant/sim_plant_01/command/water",
            payload_bytes=payload_first,
            ts=1700002000,
        )
    )

    # Should return ExecuteCommand (not cached Publish)
    assert len(actions) == 1
    assert isinstance(actions[0], ExecuteCommand)
    assert actions[0].cmd_id == "cmd-0000"
