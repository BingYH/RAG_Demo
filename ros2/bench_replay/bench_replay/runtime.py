"""Own exactly two child nodes; stop them on stdin close, STOP or timeout."""

import argparse
import json
import os
import select
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    children = []
    try:
        commands = [
            ["ros2", "run", "bench_replay", "collector", "--port", str(args.port)],
            ["ros2", "run", "bench_replay", "publisher", "--scenario", args.scenario, "--capture-id", args.capture_id],
        ]
        for command in commands:
            children.append(subprocess.Popen(command, stdout=sys.stderr, stderr=sys.stderr, start_new_session=True))
        print(json.dumps({"event": "started", "capture_id": args.capture_id,
                          "collector_pid": children[0].pid, "publisher_pid": children[1].pid}), flush=True)
        while True:
            readable, _, _ = select.select([sys.stdin], [], [], .25)
            if readable:
                sys.stdin.readline()
                break
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A ROS replay node exited unexpectedly.")
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=5)
        print(json.dumps({"event": "stopped", "capture_id": args.capture_id}), flush=True)


if __name__ == "__main__":
    main()
