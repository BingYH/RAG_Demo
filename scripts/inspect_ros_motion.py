"""Read and verify one frozen WSL ROS capture without model calls."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.http_motion import HttpMotionSession
from simulator.motion_tools import TOOL_DESCRIPTIONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--capture-id", help="Require the capture ID printed by the bridge")
    parser.add_argument("--tool", choices=TOOL_DESCRIPTIONS, default="read_motion_test_results")
    args = parser.parse_args()
    try:
        session = HttpMotionSession(args.port, expected_capture_id=args.capture_id)
        result = session.call(args.tool, {"bench_id": "BENCH-001", "test_id": session.test_id})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ValueError as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
