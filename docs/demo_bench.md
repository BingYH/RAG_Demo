# Synthetic bench definition: Demo Bench v1

Status: initial design baseline. Knowledge, three fixtures, read-only diagnosis,
LangGraph retrieval/correction/SQLite recovery and local ticket draft/edit/
approve/cancel/idempotent creation are implemented. See [Workflow](langgraph_workflow.md)
and [Tickets](ticket_workflow.md). This document defines the shared contract for
knowledge, tools and evaluation cases.

## 1. Positioning and components

BENCH-001 is a fictional single-arm functional-test bench inspired by Franka FCI
architecture. The initial fault story is failed initialization after workstation
updates. This baseline checks connection readiness, configuration and diagnostics;
it does not execute movement or tune PID.

~~~text
Engineer → Streamlit → LangGraph → Claude / RAG
                           ├─ Read-only tools → synthetic local state/logs
                           └─ Confirmed ticket creation → local records

Simulated engineering system:
Workstation → Demo Client → dedicated Ethernet → Demo Controller → seven-axis arm
                 └─ State acquisition and initialization logs
~~~

| Component | Initial definition |
| --- | --- |
| Workstation | Fictional Ubuntu 24.04 host being diagnosed, not the developer's Windows PC |
| Demo Client | Fictional robot client/startup program with version, connection and initialization records |
| Network | One workstation interface and controller endpoint; preset observations, no scanning or actual IP connections |
| Demo Controller | Fictional handshake, external-interface and state-stream observations |
| Arm | Fictional seven-axis arm; initial scope has no dynamics, trajectory execution or control data |
| ROS 2 | Jazzy architectural background; initial fixtures start no nodes, and ros2_nodes is not collected |

RAG indexes curated public-background/synthetic procedures under knowledge/.
Raw repos, this design, scenarios and evaluation answers are excluded. This is
an authoring baseline for later searchable documents.

## 2. Real background versus synthetic rules

[Sources](sources.md) cover FCI architecture, network requirements, connection
versus UDP timeouts, compatibility and ROS 2 bring-up parameters.

Bench identifiers, addresses, versions, protocols, fields, state machine, windows
and error codes are project-designed. Demo Client is not libfranka; Demo
Controller protocols are not actual FCI protocol versions. Synthetic versions
cannot establish real-product compatibility.

libfranka-common is a source reference for protocol types, handshake versions
and state definitions. Robot/gripper protocol versions are separate and are not
the libfranka package version. This initial version implements neither the
protocol nor its binary parsing.

| Baseline item | Value |
| --- | --- |
| Bench / model | BENCH-001 / DEMO-ARM-7 |
| Workstation | 192.0.2.10/24, documentation-only simulated address |
| Registered controller | 192.0.2.11, a registry value rather than guaranteed current fact |
| Default target | 192.0.2.11 |
| Baseline client | demo-client 1.4.0, synthetic protocols [1] |
| Updated client | demo-client 2.0.0, synthetic protocols [2] |
| Controller | demo-controller 1.3.0, reports synthetic protocol 1 |
| Compatibility | Observed controller protocol must belong to the current client's supported set, per synthetic guidance |
| Available state stream | At least one valid record in a two-second observation window; diagnostic availability, not real-time control acceptance |

## 3. Initialization state and success

Stages: not_started → config_loaded → endpoint_reachable → handshake_accepted →
state_received → diagnostic_ready. Failure retains last_completed_stage,
failed_stage, error_code, error_message and log evidence. These describe the
startup program's observed failure, not the established root cause.

diagnostic_ready means this configuration loaded, connection/handshake succeeded
and a state stream was readable. It does not establish movement authorization,
safety approval, calibration or complete functional acceptance.

Healthy cases need not create tickets. Fault cases gather/cite evidence and
suggest verification. Missing evidence stays unknown; do not force a hardware
damage conclusion or claim a repair.

## 4. Read-only interfaces and observable fields

Local functions may later be replaced by ROS/REST adapters. They are project
interfaces, not vendor APIs. Tools query only the session-bound BENCH-001.

| Tool | Input | Returned information |
| --- | --- | --- |
| read_bench_inventory | bench_id | robot_model, registered workstation/controller addresses, expected software baseline and registration time; asset_registry, not live observation |
| read_runtime_config | bench_id | client_version, supported_protocols, config_revision, target_ip, execution_mode=fixture, startup attempt and change summary |
| read_connection_observations | bench_id | link_up, ping, handshake and actually obtained controller_version/reported_protocol; remote fields unknown if unreachable |
| read_initialization_status | bench_id | stages, error, external_interface_enabled, state count/window and ros2_nodes; missing is not false |
| read_diagnostic_log | bench_id, limit default 20, range 1–100 | Recent synthetic event_id/time/level/component/message/startup attempt, ascending by time |

Ping always contains status, sent/received counts and RTT; no reply gives null
RTT. Handshake states: accepted, rejected, not_attempted, unknown. Remote values
must have actually been obtained during the current handshake.

Common response envelope:

~~~json
{
  "bench_id": "BENCH-001",
  "snapshot_id": "SNAP-001",
  "evidence_id": "EV-001",
  "source_type": "synthetic",
  "observed_at": "2026-11-07T10:00:00Z",
  "status": "ok",
  "data": {},
  "unavailable_fields": []
}
~~~

- status is ok, partial or error. ok means acquisition succeeded, not that the
  bench passed; an observed ping timeout is valid evidence.
- Unknowns use null with field/reason in unavailable_fields, such as
  endpoint_unreachable or not_collected. Never fill with normal defaults.
- Tool failure uses status=error, data=null and a short error.code/message.
  Tool failures are not robot fault conclusions.
- Registry observed_at is registration time; other times are synthetic
  observations. Preserve conflicting sources and explain their differences.
- Each session binds an immutable snapshot with timezone-aware ISO 8601.
  Historical snapshots are interpreted relative to snapshot time, not marked
  stale against the current PC clock.
- Neutral snapshot IDs exclude healthy/version_mismatch/connection_timeout.
  Fixture paths, scenario names, expected causes and answers do not reach the model.
- Identical requests against a snapshot return identical evidence IDs for
  citation/deduplication. Do not silently mix versions/configurations across snapshots.

## 5. Three initial scenarios

The developer/evaluator selects scenarios; the assistant only calls tools.
Each has neutral IDs and consistent attempt/time ordering. Expectations below
are implementation/evaluation guidance, excluded from RAG.

| Fixture | Visible synthetic state | Expected behavior |
| --- | --- | --- |
| healthy/ | Client 1.4.0, target .11, ping reply, accepted handshake/protocol 1, state records, diagnostic_ready | Confirm diagnostic initialization only; clarify continuing complaints and reproduction, without declaring all functions healthy |
| version_mismatch/ | Update 1.4.0 → 2.0.0, target .11, ping reply, rejected handshake with observed version/protocol 1 versus supported [2], no stream | Cite synthetic compatibility, identify incompatible combination and propose reviewed alignment/retest; no installation/rollback |
| connection_timeout/ | Target .12 versus registry .11, link up, ping timeout, no handshake, remote versions unknown, last stage config_loaded and wait-timeout log | Prioritize address discrepancy without proving .11 reachable, excluding stale registry or other network problems; request human checks and optionally draft a ticket |

Codes use DEMO_ prefixes such as DEMO_CONNECT_TIMEOUT and DEMO_PROTOCOL_MISMATCH.
Real vendor errors retain original context in public knowledge; synthetic logs
must not impersonate actual device records.

state.json contains observations, sources and change records; diagnostic.log
contains corresponding events. Expectations, scenario mapping and evaluation
labels stay application-side. The simulator does not change state based on the
model's guess or automatically become healthy after advice.

## 6. Questions, conclusions and tickets

The opening may simply say initialization failed after an update. Read available
tool data first; ask only for missing failure time, full user-visible error,
update scope or reproduction details.

Distinguish facts with evidence IDs, applicable rules with chunk IDs, hypotheses
and next steps. Preserve conflicts. Missing knowledge/tool failures can produce
an explicitly incomplete support draft rather than an invented cause.

Field binding is implemented: actual tool results supply fact_id, tool/field,
original value, origin, evidence/snapshot/time. Claude selects IDs and submits
interpretations/knowledge references with submit_analysis. Code renders fact
labels, values and citations. Registry/current versions and addresses appear as
pairs; registry data never replaces unreachable remote values. Full facts and
structured reports are saved locally/in traces. Semantic inference still needs review.

Drafts include bench, description, configurations/versions, checks, evidence/
knowledge references, unresolved questions and next steps. Humans edit, approve
or cancel. Approved writes go to data/tickets/ with IDs, deduplicated by thread
and approved revision. Edits require reapproval. Workflow-owned confirmation
cannot be bypassed with a model-supplied approved=true.

Initial tools execute no ping, network changes, restarts, installation/rollback,
movement, fault clearing, safety changes or PID adjustments. They never disguise
the Windows PC's own network state as bench evidence.

## 7. Materials and acceptance

The initial five categories are overview, synthetic versions/configuration,
initialization/evidence procedure, connection troubleshooting and support tickets.
Project rules use source_type=synthetic. Public concepts retain source IDs and versions.

Acceptance:

1. All scenarios share interfaces and consistent snapshots, times and references.
2. Unreachable remote values stay unknown; tool failure, failed checks and not-collected differ.
3. Healthy does not imply whole-product pass; mismatches cite rules; timeouts support bounded hypotheses.
4. Tools/knowledge do not leak labels/expected causes; unknown IDs and invalid limits are rejected.
5. Approval/edit/cancel/idempotent resume are verifiable without real devices.

No internal material, real logs or hardware is needed. Development uses Windows,
English project documentation/knowledge and synthetic logs. Overtemperature is
still a candidate. The [Joint-response extension](joint_response_demo.md) now has
independent evidence and graph task selection, without changing these initial
fields/scenarios.
