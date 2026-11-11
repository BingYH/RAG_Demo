# Joint-response case: simulation and evidence design

Status: three versioned CSV/state fixtures and plots, two English knowledge
documents, three read-only tools and field binding are implemented. Claude/
LangGraph supports load clarification and ticket approval. All three conditions
have live runs and LangSmith read-back. This design is excluded from RAG;
initialization/communication diagnosis remains available.

## 1. Question and scope

> A single-joint position-tracking test overshoots. Inspect conditions,
> configuration and response, identify failures against demo requirements,
> clarify missing evidence and prepare a support ticket if needed.

Show how AI associates requirements, readable evidence and gaps. Deterministic
code computes trajectories, metrics and threshold decisions. The LLM interprets,
forms supported hypotheses and advances investigation.

The fictional BENCH-001 / DEMO-ARM-7 models only abstract rotational
DEMO-JOINT-01, without identifying a real Franka joint. Six axes do not participate.
Offline Windows Python simulation needs no ROS, Gazebo or hardware at this stage.

The controller is **PD with zero integral**. It can illustrate PID-related
functional testing, but interface/configuration/report must identify actual PD
mode, not claim a complete PID controller.

## 2. Public background and limits

Reference:
references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp.
Its update() forms torque from position error times k_gains and negative filtered
velocity times d_gains, without integral. It supplies conceptual background only.

The project's model, action, parameters, sampling and thresholds are independently
designed, not a port of that controller or its filtering/reference/robot dynamics.
Knowledge citations must retain local commit and file hash.

~~~text
J × q_ddot + b × q_dot = torque
error = q_target - q
torque_requested = Kp × error - Kd × q_dot
torque = clamp(torque_requested, -torque_limit, torque_limit)
~~~

Units: q in rad, velocity rad/s, torque N·m, J kg·m², b/Kd N·m·s/rad,
Kp N·m/rad. Velocity feedback uses model velocity rather than differentiating
the step target.

This ideal inertia/viscous-damping model omits gravity, coupling, friction dead
zones, backlash, sensor noise, communication delays and actuator inner loops.
It is deterministic, with no noise/randomness. Results/parameters must not be
applied to physical arms.

## 3. Fixed action and numerical contract

| Item | Contract |
| --- | --- |
| Procedure / model / metrics | DEMO-JOINT-STEP-001 v1 / joint-inertia-pd-v1 / joint-step-metrics-v1 |
| Initial position/velocity | 0 rad / 0 rad/s |
| Window | 0–6 s inclusive |
| Target | 0 rad until 0.5 s, then 0.2 rad (about 11.46°) |
| Integration/control | 0.001 s, control updated each step |
| Output sampling | 0.01 s, 601 rows; plots/metrics use these samples |
| Integration | Semi-implicit Euler: torque/acceleration from current state, update velocity, then position with new velocity |
| Torque limit | ±2 N·m, recording requested and clamped torque |
| Baseline plant | J=0.05 kg·m², b=0.05 N·m·s/rad |
| Baseline controller | Kp=4, Kd=0.85, Ki=0, PD |

The step is an offline illustration, not a physical motion command. Integer
step indices avoid floating-point boundary shifts. Save each sample's target,
state and output computed from that state before the next integration step.

## 4. Metrics, requirements and unknowns

Compute after the step. All thresholds are project demo requirements, not Franka
or Agile Robots standards.

| Metric | Definition | Requirement |
| --- | --- | --- |
| overshoot_pct | 100 × max(0, max(q) − 0.2) / 0.2 | ≤5% |
| settling_time_s | Earliest sampled time relative to 0.5 s after which every remaining sample stays within target ±0.004 rad (2% amplitude), with ≥0.5 s remaining | ≤1.5 s |
| steady_state_error_rad | Mean target−actual over final 0.5 s, 5.5–6 s inclusive; a finite-window estimate | Absolute value ≤0.002 rad |
| peak_abs_error_rad | max(abs(target−actual)) after the step | Informational, no independent failure |
| saturation_fraction | Fraction of step-window samples with absolute requested torque greater than the limit | Informational, no independent failure |

If not settled by recording end, settling_time_s=null with
not_settled_within_observation_window. It fails if the window adequately covers
the 1.5 s limit. Too-short/corrupt data is not_evaluable, not a pass or invented
settling-time measurement.

Each result retains metric_id, value, units, requirement ID, threshold, operator,
result and window, linked to trajectory SHA256 and metrics version.
Knowledge supplies definitions/requirements; tools supply computed results.
The model must not invent or recalculate values.

response_requirement_status concerns numeric requirements for this record.
test_context_status concerns condition completeness/baseline comparability.
Unknown load still allows descriptive threshold comparisons, not whole-robot acceptance.

## 5. Three initial conditions

Generation parameters/expected behavior below are implementation/evaluation only,
excluded from model context, tools and RAG.

| Developer scenario | Generation | Expected behavior |
| --- | --- | --- |
| joint_tracking_baseline | Baseline J/b/Kp/Kd, complete conditions | Pass only for this joint/action/recorded load, not whole robot |
| joint_tracking_oscillation | Same J/b/Kp; Kd changed 0.85 → 0.10 with record, complete load context | Report overshoot/settling failures; lower damping is a priority hypothesis for engineering review/controlled retest, not automatic tuning |
| joint_tracking_load_unknown | Baseline controller; generator J=0.20, unchanged b; current payload/inertia hidden | Report failure and baseline controller settings; request tool/load/change records, retain alternatives, do not assert increased actual inertia or bad PID |

Recalculated CSV results: baseline 0% / 0.67 s; low damping about 58.53% /
2.56 s; missing load about 16.01% / 1.80 s. Generation saves/reloads CSV for
metrics; inspection verifies hash and recomputes. These approximations are not
hardcoded metric outputs.

Hidden plant parameters belong only to generator/evaluator. The assistant sees
payload_record=null, equivalent_inertia=null and not_collected. Titles, filenames,
paths, logs, IDs, attachments and trace inputs must not reveal expected causes.
Registry baselines stay explicitly registered, never filling current unknowns.

## 6. Readable evidence and files

Implemented in simulator/motion_tools.py; CLI selects with --tool:

| Tool | Contents |
| --- | --- |
| read_motion_test_conditions | Test/procedure/joint/action/window/periods, current load/fixture, registered baseline and missing fields |
| read_control_configuration | Current mode, gains, limits, revision and changes; registry baseline separate |
| read_motion_test_results | Metrics/requirements, integrity, trajectory ID/hash/count and model/metrics versions; no full CSV in model context |

Inputs are session-bound bench/test IDs, never arbitrary paths. Existing envelopes,
immutable snapshots, field binding and unknown rules apply. Computed metrics are
derived evidence with input/method provenance, not direct sensor measurements.

~~~text
docs/joint_response_demo.md                  # This design, excluded from RAG
simulator/motion.py                         # Generator, metrics, validation, plotting
simulator/motion_scenarios/<scenario>/       # Versioned state.json + trajectory.csv
scripts/generate_motion_fixtures.py          # Offline generation/validation
scripts/inspect_motion.py                    # Inspection, tools, plotting
simulator/motion_tools.py                    # Three session-bound read-only tools
knowledge/20_procedures/joint_response_test.md
knowledge/30_troubleshooting/joint_response_anomalies.md
evaluation/cases/joint_response_*.json        # Expectations separated from evidence
data/motion_reports/                         # Ignored generated plots/results
~~~

CSV fields include time_s,target_position_rad,actual_position_rad,velocity_rad_s,
requested_torque_nm,applied_torque_nm. CSV/state are versioned together; plots
belong in data/. State omits hidden generation parameters/causes.

Plots use target/actual position versus time, tolerance band, overshoot and
observation information from the same CSV, labeled offline synthetic data.
A full control panel is unnecessary initially.

## 7. AI integration

Explicit task_type selects initialization or joint_response, each with its tools,
knowledge and evidence checks. Validation, review, one correction and ticket
approval are reused. Version: bench-graph-v3-motion; older checkpoints are not
automatically migrated. See [Workflow](langgraph_workflow.md).

Read conditions/config/results → retrieve procedure/troubleshooting → check
evidence → clarify missing conditions → generate cited explanation → validate/
review → prepare requested ticket and wait for confirmation.

Ask concretely which tool/payload was used, whether it changed and whether records
exist. Oral replies remain unverified context, not snapshot changes or a new
test. Unknown replies can proceed with retained gaps, without endless questions.

Review checks unsupported PID causation, registered-as-current load, whole-robot
pass, fabricated metrics and automatic tuning. Ticket approval authorizes local
record creation only.

## 8. Implementation and acceptance

1. Generate three trajectories/metrics/plots; check nontechnical visual clarity.
2. Add tools, facts and English knowledge; keep hidden parameters out of models/retrieval.
3. Add graph task/evidence routes, reuse clarification/review/tickets and version checkpoints.
4. Validate bounded baseline conclusions, supported but nonconclusive damping
   hypotheses and missing-load clarification/gaps; inspect traces/citations.

Computational acceptance: reproducibility, correct CSV count/periods/units,
recomputable metrics, distinction among no settling/short/corrupt data, and
comfortable threshold margins. Existing initialization/ticket tests must pass.

All four stages were completed: plots visually inspected; tools, bindings,
scope isolation and retrieval checked; task routing, SQLite resume, approval and
review available. At that milestone 75 offline tests and live three-condition
traces passed: [Validation](diagnosis_validation.md). No extra products,
hardware or internal material were needed.

## 9. Local viewing and reproduction

~~~powershell
# Regenerate three versioned fixtures and three PNGs
.\.venv\Scripts\python.exe scripts/generate_motion_fixtures.py

# Validate saved data, inspect evidence and redraw without model/API calls
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --plot

# Read conditions; missing payload remains null
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --tool read_motion_test_conditions
~~~

KnowledgeIndex(applies_to="demo-joint-response-v1") indexes two documents/17
chunks. Default initialization remains five documents/25 chunks. Missing-load
queries retrieved applicable troubleshooting without scenario labels/answers.
Source commit/hash is in the manifest (six repositories, 23 files).
Finite end-to-end checks do not guarantee arbitrary model inputs.

Plots: data/motion_reports/TEST-104.png (baseline), TEST-218.png (low damping),
TEST-307.png (missing context). Developer names select inputs; plots/state use
neutral IDs. Matplotlib is in requirements.txt; plotting incurs no model cost.
Generation overwrites these three synthetic fixtures. Inspection only reads them
and optionally redraws runtime plots.
