---
doc_id: procedure.initialization_and_evidence
title: Initialization stages and diagnostic evidence collection
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-bench-v1]
source_ids: [LIBFRANKA-SETUP, ROS2-BRINGUP]
---

# Initialization stages and diagnostic evidence collection

## Synthetic initialization sequence

`not_started -> config_loaded -> endpoint_reachable -> handshake_accepted -> state_received -> diagnostic_ready`

When initialization fails, preserve `last_completed_stage`, `failed_stage`, the error code and message, and the startup attempt ID. A stage failure describes an observation, not a final hardware root cause.

For this demo, state reception requires at least one valid record in the two-second observation window. This is a diagnostic rule, not an FCI timing requirement or proof of control-loop performance.

## Collection order

1. Use `read_bench_inventory` and `read_runtime_config` to identify the bench, model, installed client, loaded configuration, configured endpoint and change history.
2. Use `read_connection_observations` to check the configured endpoint and any handshake values actually received.
3. Use `read_initialization_status` and `read_diagnostic_log` to locate the failed stage and correlate events by startup attempt and time.
4. Retrieve the applicable configuration or troubleshooting document. Ask the user only for incident context not already supplied by tools, such as their observed error, incident time, other changes and reproducibility.

## Interpretation rules

Use `evidence_id` for observations and document IDs for rules. Keep `snapshot_id` and startup attempt consistent; explain any comparisons across snapshots.

`status=ok` means the tool returned evidence successfully. It can contain a failed ping or rejected handshake. `status=partial` means some fields were unavailable. `status=error` means evidence acquisition failed and is not proof of equipment failure.

An unobserved field is `null` with an entry in `unavailable_fields`. Do not interpret null as false, zero or normal. Read historical fixtures relative to their snapshot time, not the developer computer's clock. Preserve asset registration time separately from live-observation time.

## Stopping conditions

After a bounded evidence search, summarize established facts and remaining gaps. If required information is unavailable or conflicting, ask for a targeted check or prepare a support draft. Do not invent a measurement or claim that replaying an immutable fixture performs a retest.

## Public background

LIBFRANKA-SETUP, `libfranka/docs/getting_started.rst`, discusses system and connection preparation. ROS2-BRINGUP, `franka_bringup/doc/index.rst`, distinguishes startup configuration, state publication and controllers. The stage names, tools and observation window in this document are project-defined.
