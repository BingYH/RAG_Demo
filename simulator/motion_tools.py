"""Session-bound motion evidence. Never simulate, mutate or control hardware."""

import copy
import hashlib
import math

from simulator.motion import MODEL_VERSION, ROOT, SCENARIOS, verify_fixture

TOOL_DESCRIPTIONS = {
    "read_motion_test_conditions": "Read this recorded motion test's action, sampling, payload context and separately labelled registered baseline. Missing current values remain unknown.",
    "read_control_configuration": "Read the recorded PD gains, torque limit, configuration revision and recorded changes; distinguish current settings from registry values.",
    "read_motion_test_results": "Read trajectory-verified derived metrics, demo requirements, calculation windows and provenance. This returns no raw trajectory or filesystem paths and does not run a retest.",
}


def tool_specs() -> list[dict]:
    return [{"name": name, "description": description, "input_schema": {
        "type": "object", "properties": {
            "bench_id": {"type": "string", "enum": ["BENCH-001"]},
            "test_id": {"type": "string", "minLength": 1}},
        "required": ["bench_id", "test_id"], "additionalProperties": False,
    }} for name, description in TOOL_DESCRIPTIONS.items()]


class MotionSession:
    """An application selects a fixture once; tools can only read its snapshot."""

    def __init__(self, scenario: str):
        if scenario not in SCENARIOS:
            raise ValueError("Unknown motion scenario.")
        try:
            state, rows = verify_fixture(ROOT / scenario)
            self._validate(state, rows)
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            raise ValueError("Motion snapshot could not be loaded or validated.") from None
        self._state = copy.deepcopy(state)

    @staticmethod
    def _validate(state: dict, rows: list[dict], allowed_modes=("offline_synthetic",)) -> None:
        if (set(state) != {"schema_version", "bench_id", "snapshot_id", "test_id", "observations"}
                or state["schema_version"] != "motion-1.0" or state["bench_id"] != "BENCH-001"
                or set(state["observations"]) != set(TOOL_DESCRIPTIONS)):
            raise ValueError("Unsupported snapshot.")
        public_keys = {
            "read_motion_test_conditions": {"test_id", "joint_id", "procedure_id", "execution_mode", "action",
                "observation_window_s", "sample_period_s", "control_period_s", "payload_record",
                "equivalent_inertia", "test_context_status", "registered_baseline"},
            "read_control_configuration": {"mode", "kp", "ki", "kd", "torque_limit_nm", "config_revision",
                "registered_baseline", "change_records"},
            "read_motion_test_results": {"metrics_version", "sample_count", "data_integrity",
                "response_requirement_status", "metrics", "trajectory_id", "trajectory_sha256", "model_version", "procedure_id"},
        }
        ids = set()
        for name, envelope in state["observations"].items():
            if (envelope["bench_id"] != state["bench_id"] or envelope["snapshot_id"] != state["snapshot_id"]
                    or envelope["source_type"] != "synthetic" or set(envelope["data"]) != public_keys[name]):
                raise ValueError("Inconsistent motion evidence.")
            ids.add(envelope["evidence_id"])
            data = envelope["data"]
            if name == "read_motion_test_conditions":
                expected = [{"field": f, "reason": "not_collected"} for f in
                            ("payload_record", "equivalent_inertia") if data[f] is None]
                if (data["test_id"] != state["test_id"] or envelope["unavailable_fields"] != expected
                        or data["test_context_status"] != ("incomplete" if expected else "complete")
                        or envelope["status"] != ("partial" if expected else "ok")):
                    raise ValueError("Inconsistent test conditions.")
                if (data["procedure_id"] != "DEMO-JOINT-STEP-001 v1"
                        or data["execution_mode"] not in allowed_modes
                        or data["action"] != {"initial_rad": 0., "target_rad": .2, "step_at_s": .5}
                        or data["observation_window_s"] != [0., 6.]
                        or data["sample_period_s"] != .01 or data["control_period_s"] != .001):
                    raise ValueError("Unsupported test procedure.")
            elif envelope["status"] != "ok" or envelope["unavailable_fields"]:
                raise ValueError("Inconsistent evidence status.")
            if name == "read_control_configuration" and (data["mode"] != "PD" or data["ki"] != 0):
                raise ValueError("Unsupported controller.")
            if name == "read_motion_test_results" and (data["model_version"] != MODEL_VERSION
                    or envelope["observation_origin"] != "derived_calculation"):
                raise ValueError("Inconsistent calculation provenance.")
        if len(ids) != len(TOOL_DESCRIPTIONS):
            raise ValueError("Evidence IDs must be unique.")
        config = state["observations"]["read_control_configuration"]["data"]
        if (not all(type(config[key]) in (float, int) and math.isfinite(config[key])
                    for key in ("kp", "ki", "kd", "torque_limit_nm"))
                or config["torque_limit_nm"] != 2.):
            raise ValueError("Invalid control parameters.")
        for row in rows:
            expected = config["kp"] * (row["target_position_rad"] - row["actual_position_rad"]) - config["kd"] * row["velocity_rad_s"]
            if abs(row["requested_torque_nm"] - expected) > 1e-10:
                raise ValueError("Trajectory and recorded configuration disagree.")

    @property
    def test_id(self) -> str:
        return self._state["test_id"]

    def _error(self, code: str, message: str) -> dict:
        return {"bench_id": self._state["bench_id"], "snapshot_id": self._state["snapshot_id"],
                "evidence_id": "ERR-" + self._state["snapshot_id"] + "-" + hashlib.sha256(code.encode()).hexdigest()[:8],
                "source_type": "synthetic", "observation_origin": "tool_validation",
                "observed_at": self._state["observations"]["read_motion_test_conditions"]["observed_at"],
                "status": "error", "data": None, "unavailable_fields": [],
                "error": {"code": code, "message": message}}

    def call(self, tool_name: str, arguments: dict) -> dict:
        if not isinstance(tool_name, str) or tool_name not in TOOL_DESCRIPTIONS:
            return self._error("UNKNOWN_TOOL", "Requested motion tool is unavailable.")
        if not isinstance(arguments, dict) or set(arguments) != {"bench_id", "test_id"}:
            return self._error("INVALID_ARGUMENTS", "Use exactly bench_id and test_id.")
        if arguments["bench_id"] != self._state["bench_id"]:
            return self._error("UNKNOWN_BENCH", "Requested bench is not bound to this session.")
        if arguments["test_id"] != self.test_id:
            return self._error("UNKNOWN_TEST", "Requested test is not bound to this session.")
        return copy.deepcopy(self._state["observations"][tool_name])
