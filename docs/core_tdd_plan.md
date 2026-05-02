# Core Layer TDD Plan

This document defines a test-driven development (TDD) plan for implementing the
device core layer described in `docs/core_contract.md`.

## 1. Scope and Goals

Implement the core layer as a platform-agnostic module that:

- Accepts events from hardware/runtime adapters
- Returns actions for adapters to execute
- Owns topic/payload protocol behavior
- Handles command processing and command deduplication (`cmd_id`)

Out of scope for this plan:

- TLS/auth credentials
- Schema versioning/backward compatibility
- Advanced retry logic

## 2. TDD Strategy

Use a strict red-green-refactor cycle:

1. **Red**: write a failing test for one behavior.
2. **Green**: implement the minimum core logic to pass.
3. **Refactor**: improve design without changing behavior.

Rules:

- No production code without a failing test.
- Keep tests deterministic (fixed timestamps and payloads).
- Prefer table/parameterized tests for validation cases.

## 3. Test Suite Structure

Create a standalone core test suite that does not need:

- Real MQTT broker
- Real hardware
- Real network stack

Suggested structure:

- `tests/core/test_startup.py`
- `tests/core/test_topics.py`
- `tests/core/test_payload_validation.py`
- `tests/core/test_commands.py`
- `tests/core/test_deduplication.py`
- `tests/core/test_telemetry_status.py`
- `tests/core/test_error_handling.py`

Test doubles:

- Fake clock (returns controlled `ts`)
- Fake adapter harness (submits events, captures returned actions)

## 4. Incremental Implementation Phases

### Phase 1: Skeleton + startup behavior

Write tests first:

- Core can be instantiated with config (`plant_id` required).
- `start(config)` returns no crash and expected initial actions.
- Boot event produces status publish action (`online=true`) with valid topic.

Then implement minimal state + startup handling.

### Phase 2: Topic construction and parsing

Write tests first:

- Correct telemetry topic generation from `plant_id` and `metric`.
- Correct status topic generation.
- Correct command and command ack topic parsing.
- Invalid topic shape is rejected safely.

Then implement topic helpers and parser.

### Phase 3: Payload validation

Write tests first:

- Valid telemetry payload accepted (`value`, `ts`).
- Valid status payload accepted (`online`, `ts`).
- Valid command payload accepted (`cmd_id`, `ts`, args optional).
- Invalid JSON rejected.
- Missing required fields rejected.
- Wrong field types rejected.

Then implement minimal validator functions.

### Phase 4: Command handling

Write tests first:

- Incoming command event yields `ExecuteCommand` action.
- `CommandResult(ok=true)` yields ack publish with `ok=true`.
- `CommandResult(ok=false)` yields ack publish with error string.
- Unknown command topic/payload produces log action, no actuator action.

Then implement command flow state.

### Phase 5: Command deduplication (`cmd_id`)

Write tests first:

- First command with new `cmd_id` executes exactly once.
- Duplicate command with same `cmd_id` does not execute again.
- Duplicate command re-emits prior ack if available.
- **Ack cache is bounded to prevent unbounded memory growth** (e.g., `MAX_ACK_CACHE_SIZE = 1000`).
- **Cache evicts oldest entries when max size exceeded** (LRU behavior).
- **Recently used entries are retained** (move to end on cache hit).
- **Evicted old `cmd_id` no longer hits cache** (treated as new command).

Then implement in-memory dedup cache with bounded size using `collections.OrderedDict`.

### Phase 6: Telemetry and status publish behavior

Write tests first:

- `MetricSample` event yields telemetry publish action.
- Telemetry action uses default qos/retain values.
- Status event yields status publish action with retained flag.

Then implement telemetry/status action generation.

### Phase 7: Error-path hardening

Write tests first:

- Malformed inbound message never crashes core.
- Unknown event type returns log action and safe no-op.
- Empty payload handling does not panic.

Then implement guarded error handling paths.

### Phase 8: Refactor + contract freeze

After all behavior tests pass:

- Refactor internals for clarity.
- Keep external event/action contract unchanged.
- Add regression tests for previously fixed bugs.

## 5. Test Case Matrix (Minimum)

Minimum must-pass cases before adapter integration:

1. Boot emits online status publish action.
2. Valid command yields one `ExecuteCommand` action.
3. Command result yields valid ack publish action.
4. Duplicate `cmd_id` does not re-execute command.
5. Valid telemetry event yields telemetry publish action.
6. Invalid JSON command payload is safely ignored/logged.
7. Invalid command topic shape is safely ignored/logged.
8. **Ack cache bounded after many unique `cmd_id`s** (no unbounded growth).
9. **Recently used cache entries retained** (LRU eviction).
10. **Duplicate within cache still re-emits ack** (cache hit behavior).
11. **Evicted old `cmd_id` no longer hits cache** (cache miss after eviction).

## 6. Adapter Integration Gate (Post-Core)

Only begin adapter implementation when core tests are green.

Adapter integration acceptance checks:

- Adapter can translate real MQTT callback into core `MqttMessage` event.
- Adapter executes `Publish` and `ExecuteCommand` actions correctly.
- End-to-end command -> ack path works with local broker.

### Simulator as First Adapter

The plant simulator in `/mqtt/simulator` should be refactored to use the core layer
as its first adapter integration. This provides:

- End-to-end validation of the core layer contract
- Reference implementation for future hardware adapters (Raspberry Pi, ESP32, Arduino)
- Proof that the event/action boundary works with real MQTT broker

Simulator adapter responsibilities:

- Translate `paho.mqtt.client` callbacks into core events (`MqttConnected`, `MqttDisconnected`, `MqttMessage`)
- Execute core actions: `Publish` → `client.publish()`, `ExecuteCommand` → simulate actuator, `Log` → `logging`
- Generate sensor events: `MetricSample` from moisture sensor simulation
- Handle `Tick` events for periodic telemetry/heartbeat
- Manage lifecycle: boot → connect → run loop → shutdown

Simulator should maintain existing behavior:

- Publishes moisture telemetry every `TELEMETRY_INTERVAL` seconds
- Publishes online status on connect and every `STATUS_HEARTBEAT_INTERVAL` seconds
- Subscribes to commands on `planty/plant/{plant_id}/command/+`
- Acknowledges all commands with `ok: true`

Implementation approach:

1. Keep existing `MoistureSensor` class (sensor simulation logic)
2. Replace direct MQTT publish logic with core layer event/action flow
3. Add adapter glue: MQTT callbacks → core events, core actions → MQTT operations
4. Preserve all existing tests (update implementation details as needed)
5. Add new integration tests validating core layer usage

## 7. Definition of Done

Core layer is "done" when:

- All core unit tests pass.
- No test needs real MQTT/hardware.
- Core follows `docs/core_contract.md` event/action boundary.
- All required minimum cases in section 5 pass.
- Basic adapter integration smoke test passes on at least one hardware target.
- Simulator successfully uses core layer and maintains existing behavior.

## 8. Suggested Work Order (Short Checklist)

1. Add empty core module + empty tests. ✅
2. Implement startup path via TDD. ✅
3. Implement topics via TDD. ✅
4. Implement payload validation via TDD. ✅
5. Implement commands + ack via TDD. ✅
6. Implement deduplication via TDD. ✅
7. Implement telemetry/status publish via TDD. ✅
8. Harden error handling via TDD. ✅
9. Refactor and freeze contract. ✅
10. Refactor simulator to use core layer as first adapter integration. ⬅️ NEXT
