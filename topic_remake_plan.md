Hard cutover plan (no dual-support): introduce the new topic schema everywhere, deploy backend + devices in a coordinated window, then only accept/publish the new topics. This is phased: start with telemetry only, add others later.

**1) Lock the New Topic Schema (write the spec first)**
- Root: `planty/...` (unversioned for hard cutover)
- Entity naming: use one canonical id term everywhere: `{plant_id}` (matches DB)
- Directionality: keep topics device-scoped; distinguish uplink vs downlink by category

Proposed topics (full schema, but implement incrementally):
- Telemetry (device -> motherplant): `planty/plant/{plant_id}/telemetry/{metric}` (e.g., moisture)
- Events (device -> motherplant): `planty/plant/{plant_id}/event/{event_type}` (optional now)
- Status/presence (device -> motherplant, retained + LWT): `planty/plant/{plant_id}/status`
- Commands (motherplant -> device): `planty/plant/{plant_id}/command/{command}`
- Command ack/result (device -> motherplant): `planty/plant/{plant_id}/command/{command}/ack`

Payload contracts (keep close to what you already parse):
- Telemetry: `{ "value": <number>, "ts": <unix_seconds> }` (+ optional `unit`)
- Status: `{ "online": <bool>, "ts": <unix_seconds>, ...optional metadata }`
- Command: `{ "cmd_id": "<uuid or int>", "ts": <unix_seconds>, ...args }`
- Ack: `{ "cmd_id": "<same>", "ts": <unix_seconds>, "ok": <bool>, "error": "<string|null>" }`

Broker semantics to specify:
- Retain: `status` and `config` (if added); not telemetry/command/ack by default
- QoS: telemetry QoS0/1; commands QoS1; status QoS1 + retained + LWT

**Phased Implementation Plan**

**Phase 1: Telemetry Only**
- Implement telemetry topic: `planty/plant/{plant_id}/telemetry/moisture`.
- Update backend parser and subscriptions for this topic.
- Update models: Limit `Telemetry.TELEMETRY_TYPES` to only `("moisture", "Soil moisture")`. Remove `last_temperature` field from `PlantState` model.
- Remove temperature code: Delete `if metric == "temperature": state.last_temperature = value` from `on_message` in `mqtt_client.py`. Create/run migration to drop `last_temperature` column.
- Update tests: Change `valid_topic` to `"planty/plant/plant01/telemetry/moisture"` and adjust `parse_topic` tests for the new 5-part structure.
- Update docs and examples:
  - `README.md`: Change mosquitto examples to publish/subscribe to `planty/plant/plant01/telemetry/moisture`.
  - `docs/current-flowchart.md`: Update flowchart to new topic path and remove unimplemented topics.
  - `AGENTS.md`: Update topic examples to new structure.
- Ensure backend `on_message` only processes moisture (model choices enforce this).
- Cutover: Hard cutover for telemetry.
- Verification: Publish moisture to new topic → DB stores Telemetry (type="moisture") and updates PlantState.last_moisture.

**Phase 2: Add Status/Presence**
- Implement status topic: `planty/plant/{plant_id}/status`.
- Update backend to handle status messages and LWT.
- Update models: No change needed (use existing `PlantState.online`, `last_seen`).
- Add device LWT and status publishing.
- Update docs/flowchart for status.

**Phase 3: Add Commands and Acks**
- Implement command topics: `planty/plant/{plant_id}/command/{command}` and `/command/{command}/ack`.
- Update backend subscriptions and handling for commands/acks.
- Update models: Add `CommandLog` model for ack persistence.
- Add device command subscription and ack publishing.

**Phase 4: Add Events (optional)**
- Implement event topic: `planty/plant/{plant_id}/event/{event_type}`.
- Update backend to handle events.
- Update models: Add `Event` model.

**4) Data / Model Updates (if needed, per phase)**
- Phase 1: Limit `Telemetry.TELEMETRY_TYPES` in `models.py` to only `("moisture", "Soil moisture")` (remove temperature for now; add back in later phases if needed).
- Phase 3: Add `CommandLog` model for command ack persistence: fields like plant (FK), command (str), cmd_id (str), sent_at (datetime), ack_at (datetime), ok (bool), error (str), raw_payload (json).
- Phase 4: If events added, add `Event` model: fields like plant (FK), event_type (str), value (float), timestamp (datetime).

**5) Docs + Examples Update (per phase)**
- Phase 1: Update `README.md` mosquitto examples to new telemetry topic.
- Later phases: Update `docs/current-flowchart.md` as features are added.

**6) Cutover Execution (coordinated deployment, per phase)**
For each phase, perform hard cutover in a maintenance window:
1. Deploy backend changes.
2. Deploy device changes.
3. Restart devices; verify new features.
4. Clear any old retained messages if applicable.

**7) Verification Checklist (per phase)**
- Phase 1: `mosquitto_sub` on `planty/plant/+/telemetry/+` shows moisture data; DB updates `PlantState.last_moisture`.
- Phase 2: Status retained; `online` toggles on disconnect.
- Phase 3: Commands sent/received; acks logged.
- Phase 4: Events published/handled.

**8) Rollback Plan (per phase)**
- Rollback to previous phase or old system by redeploying prior backend/device code.</content>
<parameter name="filePath">/home/richard/source/repos/Planty3/topic_remake_plan.md