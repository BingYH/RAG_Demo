# ROS trajectory replay and HTTP evidence adapter

The project-owned ROS 2 package is built in WSL. All three conditions completed
actual ROS message delivery and Windows HTTP reads. The read-only Windows adapter
and Streamlit Local JSON / WSL ROS selector are implemented, including a live
English report/draft path: [Dashboard](dashboard.md). CLI graph_bench.py still
uses local JSON. Replay/capture commands do not call the model directly.

## Data flow

~~~text
WSL: synthetic CSV + conditions/configuration
    → bench_trajectory_replay publisher
    → /rag_demo/motion_replay (std_msgs/String with versioned JSON)
    → bench_evidence_collector subscriber
    → receive 601 samples, verify sequence/hash, recalculate metrics, freeze
    → HTTP GET /snapshot (WSL 127.0.0.1:8765)
    → Windows HttpMotionSession
    → existing three read-only tools and field-fact registry
~~~

This is offline synthetic replay through ROS, not new physical measurements or
a rerun controller. Evidence uses `source_type=synthetic` and
`execution_mode=ros_synthetic_replay`; conditions/configuration originate from
`ros_topic_observation`, metrics from `derived_calculation`.
`fixture_observed_at` preserves the original record time; `observed_at` is this
capture's completion time and does not change the synthetic nature.

## Build and run

For the first build or after shared-module/ROS-package changes, run in PowerShell:

~~~powershell
wsl -d Ubuntu-24.04 --user byhan --cd /home/byhan -- bash /mnt/c/E/Workspace_BH/Tech_Review/RAG_Demo/scripts/build_ros_replay.sh
~~~

The script copies the minimal package, standard-library shared modules and three
fixtures into `~/rag_demo_ros_ws/src/bench_replay`, then builds with colcon.
It excludes knowledge, keys, Windows environments and external repositories,
and leaves .bashrc unchanged.

Start a replay from the project root and keep HTTP running:

~~~powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation
~~~

After roughly six seconds it prints capture ID, a fresh test ID, 601 samples,
response result and context completeness. Keep that terminal open.
Output distinguishes capture success from motion acceptance:
`DATA CAPTURE: SUCCESS` / `capture_status=success` means ROS → HTTP → Windows
delivery/validation succeeded. `response_requirement_status=fail` /
`RESPONSE EVALUATION: FAIL` means the response violates demo requirements.
Both can be true. `SERVICE STATUS: stopped` means cleanup completed;
`RUN STATUS: SUCCESS` means program execution succeeded. Exit code 0 does not
mean motion passed. These replace ambiguous response_status/BRIDGE_STOPPED output.

Read in another PowerShell:

~~~powershell
.\.venv\Scripts\python.exe scripts/inspect_ros_motion.py --tool read_motion_test_results
.\.venv\Scripts\python.exe scripts/inspect_ros_motion.py --tool read_motion_test_conditions
~~~

Optionally use `--capture-id` to verify identity. Ctrl+C in the bridge terminal
stops only its two nodes/HTTP service, not unrelated ROS processes.
For automatic verification and shutdown:

~~~powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_load_unknown --verify-only
~~~

The developer selects the same scenario names as the local simulator; messages/
evidence do not carry names or expected causes. Default port is 8765; override
`--port` consistently. This version uses domain 73, localhost discovery and a
fixed topic, with one bridge pair at a time.

## Consistency and failure behavior

- The publisher validates its fixture, waits for discovery, then sends begin,
  601 sequential samples and end. The subscriber does not read fixtures or copy saved metrics.
- It checks capture identity, contiguous sequence, count and trajectory SHA256,
  recomputes metrics and checks trajectory consistency with conditions/configuration.
- Reliable QoS and depth 1000 do not replace application checks. Missing,
  duplicate, reordered, mixed-capture or hash-invalid samples cannot form a snapshot.
- GET /snapshot returns 503 until completion or after invalid capture.
  /health reports collecting/ready/error separately. Unknown paths return 404;
  POST returns 405. There is no directory or control endpoint.
- Each successful capture gets fresh neutral snapshot/test/evidence IDs.
  Frozen snapshots remain unchanged by later HTTP requests/messages.
- Windows fetches the complete snapshot/trajectory once, limits size, checks
  identity and recalculates metrics/hash. Tools then return deep copies from
  memory. Disconnection cannot replace that session's evidence. New clients fail
  explicitly on unavailable/invalid sources with no JSON fallback.
- transport retains capture ID, topic, count, sequence validation, original test
  reference, source trajectory hash and completion time. Field facts retain it.
  This records a trusted local capture chain, not remote-device authentication.

## 2026-11-09 validation

| Replay | Verified samples | Recalculated overshoot | Result | Context |
| --- | --- | --- | --- | --- |
| Baseline | 601 | 0% | pass | complete |
| Oscillation | 601 | 58.53% | fail | complete |
| Missing load | 601 | 16.01% | fail | incomplete; payload/inertia remain null |

All three validation replays exited. Outputs reside at ignored
`data/wsl_validation/ros-capture-<id>.json`. Additional checks confirmed identical
bytes on repeated HTTP reads, new-client failure after shutdown, and use of a
live captured session in `build_workflow(session=...)`: missing load entered
awaiting_input with zero model usage and retained capture provenance.

A shutdown race between rclpy signal handling and explicit cleanup was fixed with
try_shutdown(), rebuilt and verified. At that milestone 83 offline tests covered
existing behavior, capture failures, metric tampering, frozen snapshots and no fallback.

References: [Official Python publisher/subscriber tutorial](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
and [QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html).
String messages carry an explicit JSON contract. No custom .msg, rosbag, Gazebo
or control real-time validation is implemented.
