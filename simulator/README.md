# Synthetic state fixtures (v1)

These fixtures and local read-only tools connect to Claude, retrieval and
LangGraph through the baseline and scripts/graph_bench.py; they are not an
independent network service. Each initialization scenario contains state.json
and JSON Lines diagnostic.log. All are English synthetic data, not device or
internal-project records.

## Reading contract

- Four observations keys in state.json correspond to the four state tools and
  use the envelope defined in docs/demo_bench.md.
- log_stream holds the log envelope without data. The log tool reads the last N
  events (default 20, range 1–100), returning data.events in ascending time order.
- Log evidence IDs use <stream_id>-n<N>, distinguishing limits reproducibly.
- The application binds the scenario. Models cannot submit paths/names; each
  call returns only its envelope, not the full state, directory or README.
- execution_mode=fixture is project simulation, not running ROS fake hardware.
- snapshot_at anchors historical replay. Registry times precede startup;
  network, handshake, initialization and log times correspond.
- Registry software is an expected baseline, not current remote state.
  Unknowns/reasons remain in unavailable_fields.
- Fixtures contain no answer/root-cause fields and are not indexed.
  Design documents explain scenarios; evaluation/cases stores expectations separately.

## Initialization directories

| Directory | Records |
| --- | --- |
| healthy/ | Baseline software, connection, handshake and diagnostic state |
| version_mismatch/ | Updated client, observed controller versions/protocol and rejection |
| connection_timeout/ | Loaded config, registry, endpoint timeout and unavailable remote state |

Advice does not modify fixtures; repeated reads are not retests/repairs.
ros2_nodes=null means not collected, not a running ROS/robot claim.

Run `python scripts/validate_fixtures.py` at the project root for IDs, ordering,
unknowns, protocols and log/state consistency. Synthetic diagnostic.log inputs
have precise Git ignore exceptions; actual runtime logs belong under logs/.

## Read-only tools

No key or third-party dependency is required:

~~~powershell
python scripts/inspect_bench.py --scenario connection_timeout --tool read_connection_observations
python scripts/inspect_bench.py --scenario version_mismatch --tool read_runtime_config
python scripts/inspect_bench.py --scenario healthy --tool read_diagnostic_log --limit 3
~~~

~~~python
from simulator.tools import DiagnosticSession, tool_specs

# Application-selected scenario; retain one instance per workflow session.
session = DiagnosticSession("connection_timeout")
definitions = tool_specs()  # Five tool definitions for Claude.
result = session.call("read_connection_observations", {"bench_id": "BENCH-001"})
~~~

Sessions load once; deep-copy returns cannot modify later observations.
Models only supply bench_id and the log limit, not scenario, paths or arbitrary
tools. Invalid calls return status=error and a code. Missing/corrupt fixtures
fail session construction without leaking local paths.

`python -m unittest discover -s tests -v` checks parameter limits, unknowns,
snapshot isolation, log slicing and response boundaries. CLI exit code reports
tool execution, not bench acceptance: successfully reading a failure exits 0.

## Single-joint read-only tools

Motion is separate through simulator.motion_tools.MotionSession:
read_motion_test_conditions, read_control_configuration and read_motion_test_results.
Construction verifies CSV hash, recalculates metrics and validates envelopes.
Calls read a fixed snapshot; they do not rerun simulation or access files/devices.

~~~powershell
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --tool read_motion_test_conditions
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_oscillation --tool read_motion_test_results
~~~

~~~python
from simulator.motion_tools import MotionSession, tool_specs

session = MotionSession("joint_tracking_load_unknown")  # Application-side only.
definitions = tool_specs()
result = session.call("read_motion_test_conditions", {
    "bench_id": "BENCH-001", "test_id": session.test_id,
})
~~~

Both IDs are required; extra parameters, cross-test access, arbitrary paths and
parameter changes are rejected. CLI uses the bound test ID by default;
--test-id can exercise invalid input. Returns are deep copies. Current unknown
payload/inertia remain null/not_collected; registry baselines do not replace
them. status=ok is separate from metric pass.

rag_demo.facts.extract_facts supports motion fields, binding metrics by metric_id
rather than list position. Facts retain units, limits, decisions and derivation;
registry fields use asset_registry. KnowledgeIndex(applies_to="demo-joint-response-v1")
creates an independent content-versioned index. Default demo-bench-v1 retrieves
only the original five initialization documents. Motion connects to Claude/
LangGraph with --task joint_response: [Workflow](../docs/langgraph_workflow.md).
