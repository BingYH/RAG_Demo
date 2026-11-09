"""Pure capture contract shared by Linux subscriber and Windows HTTP client."""

import copy
import hashlib
import re
from datetime import datetime, timezone

from simulator.motion import calculate_metrics, csv_bytes
from simulator.motion_tools import MotionSession, TOOL_DESCRIPTIONS

TOPIC = "/rag_demo/motion_replay"


class Capture:
    def __init__(self):
        self.rows = []
        self.begin = None
        self.frozen = None
        self.error = None

    def accept(self, message):
        if self.frozen is not None or self.error:
            return
        try:
            self._accept(message)
        except (ValueError, TypeError, KeyError, IndexError):
            self.error = "INVALID_OR_INCOMPLETE_ROS_CAPTURE"
            raise ValueError(self.error) from None

    def _accept(self, msg):
        if not isinstance(msg, dict):
            raise ValueError("Invalid message.")
        if self.begin is None:
            if msg["kind"] != "begin" or not re.fullmatch(r"[0-9a-f]{32}", msg["capture_id"]):
                raise ValueError("Expected begin message.")
            if msg["expected_samples"] != 601:
                raise ValueError("Unsupported sample count.")
            self.begin = copy.deepcopy(msg)
            return
        if msg["capture_id"] != self.begin["capture_id"]:
            raise ValueError("Mixed captures.")
        if msg["kind"] == "sample":
            if type(msg["sequence"]) is not int or msg["sequence"] != len(self.rows) or len(self.rows) >= 601:
                raise ValueError("Dropped, duplicated or reordered sample.")
            self.rows.append(copy.deepcopy(msg["row"]))
            return
        if msg["kind"] != "end" or len(self.rows) != 601 or msg["sample_count"] != 601:
            raise ValueError("Incomplete recording.")
        sha = hashlib.sha256(csv_bytes(self.rows)).hexdigest()
        if sha != self.begin["trajectory_sha256"] or sha != msg["trajectory_sha256"]:
            raise ValueError("Trajectory hash mismatch.")
        result = calculate_metrics(self.rows)
        capture_id = self.begin["capture_id"]
        stamp = datetime.now(timezone.utc).isoformat()
        snapshot_id = "SNAP-R-" + capture_id
        conditions = copy.deepcopy(self.begin["conditions"])
        original_test = conditions["test_id"]
        conditions.update(test_id="TEST-R-" + capture_id, execution_mode="ros_synthetic_replay")
        config = copy.deepcopy(self.begin["configuration"])
        result.update(trajectory_id="TRJ-R-" + capture_id, trajectory_sha256=sha,
                      model_version=self.begin["model_version"], procedure_id=conditions["procedure_id"])
        transport = {"kind": "wsl_ros2_synthetic_replay", "capture_id": capture_id, "topic": TOPIC,
                     "received_samples": 601, "expected_samples": 601, "sequence_verified": True,
                     "replayed_test_id": original_test, "source_trajectory_sha256": sha,
                     "completed_at": stamp, "fixture_observed_at": self.begin["fixture_observed_at"]}
        state = {"schema_version": "motion-1.0", "bench_id": "BENCH-001", "snapshot_id": snapshot_id,
                 "test_id": conditions["test_id"], "observations": {}}
        for index, (name, data) in enumerate(zip(TOOL_DESCRIPTIONS, (conditions, config, result)), 1):
            unavailable = copy.deepcopy(self.begin["unavailable_fields"]) if index == 1 else []
            state["observations"][name] = {"bench_id": "BENCH-001", "snapshot_id": snapshot_id,
                "evidence_id": "EV-R-" + capture_id + f"-{index:02d}", "source_type": "synthetic",
                "observation_origin": "derived_calculation" if index == 3 else "ros_topic_observation",
                "observed_at": stamp, "status": "partial" if unavailable else "ok", "data": data,
                "unavailable_fields": unavailable, "transport": copy.deepcopy(transport)}
        MotionSession._validate(state, self.rows, allowed_modes=("ros_synthetic_replay",))
        self.frozen = {"schema_version": "ros-capture-1.0", "capture_id": capture_id,
                       "snapshot": state, "trajectory": copy.deepcopy(self.rows)}


def validate_capture(payload):
    if payload["schema_version"] != "ros-capture-1.0":
        raise ValueError("Unsupported capture schema.")
    state, rows, capture_id = payload["snapshot"], payload["trajectory"], payload["capture_id"]
    if not re.fullmatch(r"[0-9a-f]{32}", capture_id) or state["snapshot_id"] != "SNAP-R-" + capture_id:
        raise ValueError("Capture identity mismatch.")
    if state["test_id"] != "TEST-R-" + capture_id:
        raise ValueError("Capture test mismatch.")
    MotionSession._validate(state, rows, allowed_modes=("ros_synthetic_replay",))
    computed = calculate_metrics(rows)
    results = state["observations"]["read_motion_test_results"]["data"]
    sha = hashlib.sha256(csv_bytes(rows)).hexdigest()
    if results["trajectory_sha256"] != sha or any(results[k] != v for k, v in computed.items()):
        raise ValueError("Captured trajectory does not support reported metrics.")
    for index, (name, envelope) in enumerate(state["observations"].items(), 1):
        transport = envelope["transport"]
        if (transport["capture_id"] != capture_id or transport["kind"] != "wsl_ros2_synthetic_replay"
                or transport["topic"] != TOPIC or transport["received_samples"] != 601
                or transport["expected_samples"] != 601 or transport["sequence_verified"] is not True
                or transport["source_trajectory_sha256"] != sha):
            raise ValueError("Capture transport metadata mismatch.")
        expected_origin = "derived_calculation" if name == "read_motion_test_results" else "ros_topic_observation"
        if envelope["observation_origin"] != expected_origin:
            raise ValueError("Capture origin mismatch.")
    return state, rows
