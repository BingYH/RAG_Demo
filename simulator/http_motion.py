"""Fetch one immutable ROS capture from local HTTP; never fall back to fixtures."""

import copy
import json
from urllib.request import ProxyHandler, build_opener

from simulator.motion_tools import MotionSession
from simulator.ros_capture import validate_capture


class RosCaptureError(ValueError):
    """Unavailable/invalid ROS source; never substitute a fixture."""


class HttpMotionSession(MotionSession):
    def __init__(self, port=8765, expected_capture_id=None):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid local ROS bridge port.")
        try:
            opener = build_opener(ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{port}/snapshot", timeout=5) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Capture exceeds size limit.")
            payload = json.loads(raw)
            if expected_capture_id and payload["capture_id"] != expected_capture_id:
                raise ValueError("Unexpected capture identity.")
            state, rows = validate_capture(payload)
        except Exception:
            raise RosCaptureError("ROS HTTP capture is unavailable or invalid; no fixture fallback was used.") from None
        self._state = copy.deepcopy(state)
        self.trajectory = copy.deepcopy(rows)
        self.capture_id = payload["capture_id"]

    def export_capture(self):
        payload = {"schema_version": "ros-capture-1.0", "capture_id": self.capture_id,
                   "snapshot": copy.deepcopy(self._state), "trajectory": copy.deepcopy(self.trajectory)}
        validate_capture(payload)
        return payload
