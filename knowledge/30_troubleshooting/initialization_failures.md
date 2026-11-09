---
doc_id: troubleshooting.initialization_failures
title: Connection, handshake and state-reception failures
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-bench-v1]
source_ids: [FCI-TROUBLESHOOTING, LIBFRANKA-NETWORK]
---

# Connection, handshake and state-reception failures

## Connection cannot be established

`DEMO_CONNECT_TIMEOUT` is a synthetic startup error. Read the loaded target address, asset registration, link and ping observations, failed stage and logs. If addresses differ, report the discrepancy and request verification. If the checked endpoint does not reply, its current software and protocol are unknown.

Do not declare the controller defective or its address wrong solely from a timeout. A physical link, correct address, reachable endpoint, available external interface and accepted handshake are distinct checks.

## Endpoint replies but handshake is rejected

For `DEMO_PROTOCOL_MISMATCH`, compare the observed protocol with runtime client support using `configuration.version_and_endpoint`. A received handshake response can contain the controller's reported version even when the negotiation is rejected. This does not mean that state streaming became available.

If evidence establishes incompatibility, report it for this attempt and recommend configuration alignment followed by a supervised retest. The observation does not prove that all other faults are absent.

## Connection works but state is unavailable

Check whether the handshake succeeded and whether the state observation was actually collected. Do not confuse absence of collection with a measured zero-record window. Missing state can require checking interface availability or data transport; do not diagnose a particular firewall rule without evidence. This branch is documented for incomplete-evidence handling and is not an additional implemented fixture in v1.

## Public Franka error distinctions

In FCI-TROUBLESHOOTING, the chapters identified by `troubleshooting_connection_timeout`, `troubleshooting_robot_not_reachable`, `troubleshooting_udp_timeout` and `troubleshooting_incompatible_library` describe different real errors:

- `Connection timeout`: check connection prerequisites, interface availability and reachability.
- `Robot is not reachable`: inspect addressing and network setup.
- `UDP receive: Timeout`: investigate reception of robot state, including possible UDP filtering.
- `Incompatible Library Version`: consult the applicable real compatibility information.

These are public technical concepts, summarized in our own words. They are not a one-to-one mapping from demo error codes, and real product applicability must be checked. LIBFRANKA-NETWORK, `docs/system_requirements.rst`, distinguishes physical connectivity and real-time networking requirements. The demo neither measures nor certifies those requirements.

## Report structure

Return observed facts with evidence IDs, applicable rules with document references, hypotheses and unresolved questions, then a bounded next action. If evidence or documentation is insufficient, state the gap and use `support.ticket_workflow`; do not turn a plausible hypothesis into a confirmed repair.
