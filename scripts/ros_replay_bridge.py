"""Start the WSL ROS replay, fetch/validate its capture from Windows, optionally serve."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulator.http_motion import HttpMotionSession
from simulator.motion import SCENARIOS
from simulator.motion_tools import TOOL_DESCRIPTIONS


class Bridge:
    def __init__(self, scenario, port=8765):
        if scenario not in SCENARIOS or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid replay configuration.")
        self.capture_id, self.port = uuid4().hex, port
        # wslpath translates the actual project location, rather than embedding a drive path.
        path = subprocess.check_output(["wsl", "-d", "Ubuntu-24.04", "--user", "byhan", "--", "wslpath", "-a",
                                        (ROOT / "scripts/run_ros_replay.sh").as_posix()], encoding="utf-8").strip()
        self.process = subprocess.Popen(["wsl", "-d", "Ubuntu-24.04", "--user", "byhan", "--cd", "/home/byhan",
            "--", "bash", path, "--scenario", scenario, "--capture-id", self.capture_id, "--port", str(port)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        self.stopped = False

    def wait(self):
        opener = build_opener(ProxyHandler({}))
        for _ in range(120):
            if self.process.poll() is not None:
                raise RuntimeError("WSL ROS bridge exited before completing a capture.")
            try:
                with opener.open(f"http://127.0.0.1:{self.port}/health", timeout=1) as response:
                    status = json.loads(response.read(16384))
                if status.get("capture_id") not in (None, self.capture_id):
                    raise RuntimeError("Port is serving a different capture; select an unused port.")
                if status.get("status") == "error":
                    raise RuntimeError("ROS collector rejected the capture.")
                if status.get("status") == "ready":
                    return HttpMotionSession(self.port, expected_capture_id=self.capture_id)
            except (URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(.25)
        raise RuntimeError("ROS capture timed out; no fixture fallback was used.")

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.stdin.write("STOP\n")
                self.process.stdin.flush()
            output, _ = self.process.communicate(timeout=15)
            self.stopped = self.process.returncode == 0 and any(
                json.loads(line).get("event") == "stopped" for line in output.splitlines() if line.startswith("{"))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            self.process.terminate()
            self.process.communicate(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[1])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--verify-only", action="store_true", help="Capture, verify and stop instead of serving until Ctrl+C")
    args = parser.parse_args()
    bridge = Bridge(args.scenario, args.port)
    report = None
    completed = False
    try:
        session = bridge.wait()
        observations = {name: session.call(name, {"bench_id": "BENCH-001", "test_id": session.test_id}) for name in TOOL_DESCRIPTIONS}
        report = {"capture_id": session.capture_id, "test_id": session.test_id,
                  "capture_status": "success", "sample_count": len(session.trajectory), "observations": observations}
        directory = ROOT / "data/wsl_validation"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"ros-capture-{session.capture_id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        results = observations["read_motion_test_results"]["data"]
        print("\nDATA CAPTURE: SUCCESS (ROS -> HTTP -> Windows; trajectory and metrics verified)", flush=True)
        print(json.dumps({"capture_status": "success", "capture_id": session.capture_id, "test_id": session.test_id,
                         "sample_count": len(session.trajectory), "response_requirement_status": results["response_requirement_status"],
                         "overshoot_pct": next(m["value"] for m in results["metrics"] if m["metric_id"] == "overshoot_pct"),
                         "test_context_status": observations["read_motion_test_conditions"]["data"]["test_context_status"]}, indent=2), flush=True)
        if results["response_requirement_status"] == "fail":
            print("RESPONSE EVALUATION: FAIL (recorded motion exceeds demo limits; data capture succeeded)", flush=True)
        elif results["response_requirement_status"] == "pass":
            print("RESPONSE EVALUATION: PASS (this recorded action meets demo limits)", flush=True)
        else:
            print("RESPONSE EVALUATION: NOT EVALUABLE (insufficient test evidence)", flush=True)
        if not args.verify_only:
            print(f"Frozen ROS capture ready: http://127.0.0.1:{args.port}/snapshot ; Ctrl+C stops both nodes.", flush=True)
            while bridge.process.poll() is None:
                time.sleep(.5)
        completed = True
    except KeyboardInterrupt:
        completed = report is not None
    finally:
        bridge.close()
        print("SERVICE STATUS:", "stopped" if bridge.stopped else "shutdown not confirmed", flush=True)
        print("RUN STATUS:", "SUCCESS" if completed and bridge.stopped else "FAILED / INTERRUPTED", flush=True)
        print("Exit status reflects execution/cleanup, not motion requirement pass/fail.", flush=True)
    if report is None or not bridge.stopped:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
