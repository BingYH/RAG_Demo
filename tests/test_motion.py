import copy
import json
import math
import unittest

from simulator.motion import (ROOT, SCENARIOS, calculate_metrics, csv_bytes, load_trajectory,
                              simulate, verify_fixture)


class MotionTests(unittest.TestCase):
    def test_saved_trajectories_recompute_and_match_generator(self):
        for name, inertia, kd in zip(SCENARIOS, (.05, .05, .20), (.85, .10, .85)):
            state, rows = verify_fixture(ROOT / name)
            self.assertEqual(len(rows), 601)
            self.assertEqual(csv_bytes(simulate(inertia=inertia, kd=kd)), (ROOT / name / "trajectory.csv").read_bytes())
            data = state["observations"]["read_motion_test_results"]["data"]
            self.assertEqual(data["response_requirement_status"], "pass" if name == SCENARIOS[0] else "fail")
            self.assertEqual({o["snapshot_id"] for o in state["observations"].values()}, {state["snapshot_id"]})

    def test_metrics_independent_known_signals(self):
        rows = simulate(inertia=.05, kd=.85)
        for row in rows[50:]:
            row["actual_position_rad"] = .2
        result = calculate_metrics(rows)
        metrics = {m["metric_id"]: m for m in result["metrics"]}
        self.assertEqual(metrics["overshoot_pct"]["value"], 0.)
        self.assertEqual(metrics["settling_time_s"]["value"], 0.)
        self.assertEqual(metrics["steady_state_error_rad"]["value"], 0.)
        for row in rows[50:]:
            row["actual_position_rad"] = .22
        result = calculate_metrics(rows)
        metrics = {m["metric_id"]: m for m in result["metrics"]}
        self.assertAlmostEqual(metrics["overshoot_pct"]["value"], 10.)
        self.assertIsNone(metrics["settling_time_s"]["value"])
        self.assertEqual(metrics["settling_time_s"]["reason"], "not_settled_within_observation_window")
        self.assertEqual(metrics["settling_time_s"]["result"], "fail")

    def test_short_and_late_settling_are_not_passing(self):
        rows = simulate(inertia=.05, kd=.85)
        short = calculate_metrics(rows[:100])
        self.assertEqual(short["response_requirement_status"], "not_evaluable")
        self.assertTrue(all(m["result"] == "not_evaluable" for m in short["metrics"]))
        # Re-entering the band only in the last 0.1 s lacks the required dwell.
        for row in rows[50:590]:
            row["actual_position_rad"] = 0.
        metrics = {m["metric_id"]: m for m in calculate_metrics(rows)["metrics"]}
        self.assertIsNone(metrics["settling_time_s"]["value"])

    def test_corrupt_samples_rejected(self):
        original = simulate(inertia=.05, kd=.85)
        for key, value in (("actual_position_rad", math.nan), ("time_s", .015),
                           ("applied_torque_nm", 3.), ("target_position_rad", .3)):
            rows = copy.deepcopy(original)
            rows[1][key] = value
            with self.assertRaises(ValueError):
                calculate_metrics(rows)
        rows = copy.deepcopy(original)
        del rows[1]["velocity_rad_s"]
        with self.assertRaises(ValueError):
            calculate_metrics(rows)

    def test_unknown_load_remains_unknown_and_ids_are_neutral(self):
        state, _ = verify_fixture(ROOT / SCENARIOS[2])
        conditions = state["observations"]["read_motion_test_conditions"]
        self.assertIsNone(conditions["data"]["payload_record"])
        self.assertIsNone(conditions["data"]["equivalent_inertia"])
        self.assertEqual(conditions["data"]["test_context_status"], "incomplete")
        self.assertEqual({f["field"] for f in conditions["unavailable_fields"]},
                         {"payload_record", "equivalent_inertia"})
        serialized = json.dumps(state)
        for label in (*SCENARIOS, "root_cause", "expected_behavior", '"inertia": 0.2'):
            self.assertNotIn(label, serialized)


if __name__ == "__main__":
    unittest.main()
