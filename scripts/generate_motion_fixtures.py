"""Generate the three offline motion fixtures and neutral-ID response plots."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.motion import (MODEL_VERSION, ROOT, SCENARIOS, calculate_metrics, csv_bytes,
                              load_trajectory, plot_response, simulate, trajectory_hash, verify_fixture)


def generate(scenario: str) -> Path:
    # These parameters are generator-only. Never send this mapping to the model.
    cases = {SCENARIOS[0]: (.05, .85, "104"), SCENARIOS[1]: (.05, .10, "218"),
             SCENARIOS[2]: (.20, .85, "307")}
    inertia, kd, token = cases[scenario]
    unknown = scenario == SCENARIOS[2]
    directory = ROOT / scenario
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "trajectory.csv"
    path.write_bytes(csv_bytes(simulate(inertia=inertia, kd=kd)))
    results = calculate_metrics(load_trajectory(path))
    results.update({"trajectory_id": f"TRJ-{token}", "trajectory_sha256": trajectory_hash(path),
                    "model_version": MODEL_VERSION, "procedure_id": "DEMO-JOINT-STEP-001 v1"})
    conditions = {"test_id": f"TEST-{token}", "joint_id": "DEMO-JOINT-01",
                  "procedure_id": "DEMO-JOINT-STEP-001 v1", "execution_mode": "offline_synthetic",
                  "action": {"initial_rad": 0., "target_rad": .2, "step_at_s": .5},
                  "observation_window_s": [0., 6.], "sample_period_s": .01, "control_period_s": .001,
                  "payload_record": None if unknown else {"fixture_id": "DEMO-FIXTURE-A", "payload_id": "DEMO-LOAD-A"},
                  "equivalent_inertia": None if unknown else {"value": .05, "unit": "kg*m^2"},
                  "test_context_status": "incomplete" if unknown else "complete",
                  "registered_baseline": {"origin": "asset_registry", "payload_id": "DEMO-LOAD-A",
                                          "equivalent_inertia_kg_m2": .05}}
    config = {"mode": "PD", "kp": 4., "ki": 0., "kd": kd, "torque_limit_nm": 2.,
              "config_revision": "CTRL-012" if kd == .10 else "CTRL-011",
              "registered_baseline": {"origin": "asset_registry", "kp": 4., "ki": 0., "kd": .85},
              "change_records": [{"field": "kd", "from": .85, "to": .10,
                                  "recorded_at": "2026-11-08T09:50:00Z"}] if kd == .10 else []}
    state = {"schema_version": "motion-1.0", "bench_id": "BENCH-001", "snapshot_id": f"SNAP-{token}",
             "test_id": f"TEST-{token}", "observations": {}}
    for i, (name, data) in enumerate((("read_motion_test_conditions", conditions),
                                     ("read_control_configuration", config), ("read_motion_test_results", results)), 1):
        missing = [{"field": f, "reason": "not_collected"} for f in
                   ("payload_record", "equivalent_inertia")] if unknown and i == 1 else []
        state["observations"][name] = {"bench_id": "BENCH-001", "snapshot_id": f"SNAP-{token}",
            "evidence_id": f"EV-{token}-{i:02d}", "source_type": "synthetic",
            "observation_origin": "derived_calculation" if i == 3 else "synthetic_test_record",
            "observed_at": "2026-11-08T10:00:06Z", "status": "partial" if missing else "ok",
            "data": data, "unavailable_fields": missing}
    (directory / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    verify_fixture(directory)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    for scenario in SCENARIOS:
        state, rows = verify_fixture(generate(scenario))
        if not args.no_plots:
            output = Path(__file__).resolve().parents[1] / "data/motion_reports" / f"{state['test_id']}.png"
            plot_response(state, rows, output)
            print(f"Plot: {output}")
        data = state["observations"]["read_motion_test_results"]["data"]
        print(state["test_id"], data["response_requirement_status"],
              {m["metric_id"]: m["value"] for m in data["metrics"]})


if __name__ == "__main__":
    main()
