---
doc_id: procedure.joint_response_test
title: Synthetic single-joint PD step test and response requirements
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-joint-response-v1]
source_ids: [ROS2-JOINT-IMPEDANCE]
---

# Synthetic single-joint PD step test and response requirements

## Scope and source boundary

This procedure is independently designed for BENCH-001 and abstract DEMO-JOINT-01. It evaluates one offline action, not all seven joints, robot safety or hardware operation. All model parameters, sampling, actions and acceptance limits below are project-defined demo rules, not Franka or Agile Robots specifications. The implemented mode is PD with Ki=0; do not describe it as an implemented full PID controller.

## Public conceptual background

ROS2-JOINT-IMPEDANCE identifies the public franka_ros2 FR3 joint_impedance_example_controller.cpp, update(): its position-error term uses k_gains and its negative filtered-velocity term uses d_gains. It contains no integral term. This is conceptual background only. Our independent one-joint inertia/damping model does not reproduce that controller, its filter, trajectory or real robot dynamics. Source commit and SHA256 are recorded in docs/source_manifest.json; the original source is not indexed.

## Action and sampling

DEMO-JOINT-STEP-001 v1 starts at position and velocity zero. The target changes from 0 to 0.2 rad at t=0.5 s. The recording covers 0 through 6 s, sampled every 0.01 s, including both endpoints (601 rows). The offline controller/integrator period is 0.001 s. Requested torque is Kp*(target-position)-Kd*velocity; applied torque is clipped at +/-2 N*m. There is no integral action or target derivative. This discontinuous step is an offline diagnostic action, not a motion instruction for real hardware.

## Evidence collection and applicability

Read read_motion_test_conditions, read_control_configuration and read_motion_test_results for the session-bound bench and test ID. Correlate snapshot, test, procedure and configuration revision. Conditions include the current action, payload/fixture records and sampling. Registered baseline entries are historical registry information, not replacements for current missing records. Tool status ok means evidence acquisition succeeded; response_requirement_status can still be fail. Partial conditions can coexist with complete trajectory data.

## Overshoot requirement DEMO-RESP-01

For sampled positions from t=0.5 through 6 s, overshoot_pct = 100*max(0, max(actual)-0.2)/0.2. The project demo limit is <=5%. The denominator is the 0.2 rad step amplitude, not the observed peak position. Use the tool's deterministic result and attached requirement, unit and calculation window; do not estimate it from a picture or invent a replacement value.

## Settling requirement DEMO-RESP-02

The settling band is target +/-0.004 rad (2% of the step amplitude). Settling time is relative to the step at 0.5 s: the earliest sampled entry after which all remaining samples stay in the band, with at least another 0.5 s observed. The project demo limit is <=1.5 s. A settling time of 1.8 s means entry at absolute t=2.3 s. It does not mean the trace ends at 1.8 s. Repeated crossings must not be mistaken for the final settling time.

## Finite-window error requirement DEMO-RESP-03

steady_state_error_rad is the arithmetic mean of target minus actual over sampled t=5.5 through 6 s, including endpoints. Its absolute value must be <=0.002 rad under the demo procedure. This finite-window estimate does not prove the asymptotic error is zero. Passing this item does not override failed overshoot or settling requirements.

## Informational metrics

peak_abs_error_rad is the maximum absolute position error in the post-step window. saturation_fraction is the fraction of post-step output samples whose requested torque magnitude exceeds 2 N*m. These are informational, with no independent acceptance threshold. A zero sampled saturation fraction does not prove that no saturation occurred between output samples. Do not infer that another unmeasured failure mode is absent.

## Missing, incomplete and derived results

Missing current fields remain null with an unavailable_fields reason. A complete trace that never satisfies the settling definition returns null settling time with not_settled_within_observation_window and a failed settling requirement. A short observation is not_evaluable rather than a pass; invalid samples cause evidence acquisition to fail. Derived metrics retain trajectory_id, trajectory_sha256, metrics_version and model_version. They are program-calculated synthetic evidence, not physical sensor measurements.

## Reporting and retest

Separate response_requirement_status from test_context_status. Numerical comparisons remain reportable when context is incomplete, but comparability with a baseline and final engineering acceptance remain unresolved. Report actual metric/threshold pairs with evidence and document references. Passing is limited to this action and recorded conditions. Re-reading the immutable snapshot is not a retest. A new engineering retest needs new observations; this assistant cannot tune gains or execute motion.
