---
doc_id: configuration.version_and_endpoint
title: Demo Client compatibility and endpoint configuration
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-bench-v1]
source_ids: [LIBFRANKA-COMPATIBILITY, ROS2-CONFIG, FCI-PROTOCOL-TYPES]
---

# Demo Client compatibility and endpoint configuration

## Synthetic compatibility rule

These versions and protocol numbers belong exclusively to Demo Bench v1. They are not real libfranka or Franka compatibility values.

| Installed client | Supported demo protocols |
| --- | --- |
| demo-client 1.4.0 | [1] |
| demo-client 2.0.0 | [2] |

The demo-controller 1.3.0 implementation reports demo protocol 1 when its handshake response is observable. Compatibility requires that the observed controller protocol is in the installed client's supported set. Do not derive compatibility from version ordering alone.

Compare values from the same startup attempt. If the controller cannot be reached, its current protocol remains unknown: the registered controller version is not a handshake observation. Unknown client versions or unobserved protocols require more evidence or escalation.

## Endpoint configuration

The baseline workstation address is `192.0.2.10/24`. The asset register lists controller address `192.0.2.11`. Both are documentation-only addresses used in fixtures; no network request should be sent to them.

The authoritative address for the current attempt is runtime `target_ip`, together with `config_revision`. Compare it with the asset register. A difference is a configuration discrepancy to investigate, not proof that either value is correct or that the registered address is reachable.

Link up indicates local interface status only. A ping reply does not establish protocol compatibility, state-stream availability or real-time performance.

## Next actions

For an observed protocol incompatibility, propose aligning software to a documented compatible configuration and repeating initialization under engineer supervision. Do not automatically upgrade or roll back software. For an address discrepancy, request verification of the intended controller and configuration before proposing a change.

## Public background

LIBFRANKA-COMPATIBILITY, `libfranka/docs/compatibility_matrix.rst`, motivates explicit compatibility checks. ROS2-CONFIG, `franka_bringup/config/franka.config.yaml` and `launch/franka.launch.py`, motivates checking loaded endpoint and launch configuration. FCI-PROTOCOL-TYPES distinguishes protocol identifiers from package releases. These sources do not establish the synthetic table above.
