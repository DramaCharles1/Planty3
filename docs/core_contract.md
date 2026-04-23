# Core/Adapter Boundary Contract

This document defines the boundary between the device **core layer** and hardware-specific
**adapter layers**.

Scope assumptions for this project:

- Personal project (not a production product)
- No MQTT credentials
- No TLS
- No schema versioning
- No backward-compatibility guarantees
- No custom retry policy

## 1. Architectural Roles

- **Core layer**: platform-agnostic behavior and MQTT protocol semantics.
- **Adapter layer**: board/runtime integration (Raspberry Pi, ESP32, Arduino).

Dependency direction:

- Adapter depends on core.
- Core does not depend on adapter implementation details.

## 2. Responsibilities

### Core layer owns

- Topic construction and parsing
- Payload validation (enough to avoid crashes and bad writes)
- Command handling flow
- Command deduplication by `cmd_id`
- Building telemetry/status/ack payloads

### Adapter layer owns

- MQTT client library setup and connection
- Subscriptions and callback wiring
- Sensor reading and actuator control
- Main loop/timers and scheduling
- Time source (`now` timestamp)

## 3. Interface Model

Use an event/action contract.

- Adapter sends **events** to core.
- Core returns **actions** for adapter to execute.

This keeps core testable without hardware or network access.

## 4. Core API (Adapter -> Core)

Core should expose a small event-driven API:

- `core.start(config)`
- `core.handle_event(event) -> list[action]`
- `core.shutdown()`

Suggested event types:

- `Booted(ts)`
- `MqttConnected(ts)`
- `MqttDisconnected(ts)`
- `MqttMessage(topic, payload_bytes, ts)`
- `MetricSample(metric, value, ts)`
- `CommandResult(cmd_id, command, ok, error, ts)`
- `Tick(ts)` (optional)

## 5. Action Types (Core -> Adapter)

Suggested actions:

- `Publish(topic, payload_bytes, qos, retain)`
- `ReadMetric(metric)` (optional)
- `ExecuteCommand(command, args, cmd_id)`
- `Log(level, message, fields)`

For simplicity on microcontrollers, prefer adapter-driven telemetry sampling:

- Adapter reads sensors on its own schedule.
- Adapter emits `MetricSample` event to core.
- Core emits `Publish` action for telemetry.

## 6. MQTT Topic Contract

- Telemetry: `planty/plant/{plant_id}/telemetry/{metric}`
- Status: `planty/plant/{plant_id}/status`
- Command inbound: `planty/plant/{plant_id}/command/{command}`
- Command ack outbound: `planty/plant/{plant_id}/command/{command}/ack`

## 7. Payload Contract

Telemetry payload:

```json
{"value": 42.1, "ts": 1713878400}
```

Status payload:

```json
{"online": true, "ts": 1713878400}
```

Command payload (inbound from broker):

```json
{"cmd_id": "abc123", "ts": 1713878400, "duration": 2}
```

Command ack payload:

```json
{"cmd_id": "abc123", "ts": 1713878401, "ok": true, "error": null}
```

## 8. QoS and Retain Defaults

- Telemetry: `qos=0`, `retain=false`
- Status: `qos=1`, `retain=true`
- Command ack: `qos=1`, `retain=false`

## 9. Minimal Validation Rules

Core should reject invalid messages safely:

- Invalid JSON
- Missing required fields (`cmd_id`, `ts`, etc.)
- Wrong primitive types
- Unknown command topic shape

On rejection:

- Never crash
- Emit log action
- Skip processing

## 10. Command Deduplication

Deduplicate by `cmd_id`.

- If first-seen `cmd_id`: execute command and emit ack.
- If duplicate `cmd_id`: do not execute actuator again; re-emit prior ack when available.

Note: adapters may keep this cache in memory only for now.

## 11. Adapter Conformance Checklist

An adapter is considered conformant when it can:

- Connect to MQTT broker and subscribe to command topics
- Forward MQTT messages to core as `MqttMessage` events
- Execute returned `Publish` actions exactly
- Execute returned `ExecuteCommand` actions and send `CommandResult` events
- Send telemetry via `MetricSample` events
- Publish online status on startup

## 12. Non-Goals (Current Phase)

- Auth/TLS management
- OTA/update workflows
- Backward-compatible schema evolution
- Robust store-and-forward queues
- Advanced retry/backoff tuning
