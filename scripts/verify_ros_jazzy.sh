#!/usr/bin/env bash
# Run as the normal Linux user; only the two spawned demo processes are stopped.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=72
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONUNBUFFERED=1
python3 - <<'PY'
import json
import os
import signal
import subprocess
import time

processes = []
try:
    for package, executable, name in (
        ('demo_nodes_py', 'listener', 'rag_smoke_listener'),
        ('demo_nodes_cpp', 'talker', 'rag_smoke_talker'),
    ):
        processes.append(subprocess.Popen(
            ['ros2', 'run', package, executable, '--ros-args', '-r', '__node:=' + name,
             '-r', 'chatter:=/rag_demo_smoke/chatter'], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True))
    time.sleep(8)
finally:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
outputs = []
for process in processes:
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate(timeout=5)
    outputs.append(output)
received = [line for line in outputs[0].splitlines() if 'I heard' in line]
published = [line for line in outputs[1].splitlines() if 'Publishing' in line]
result = {'ros_distro': os.environ.get('ROS_DISTRO'), 'domain_id': 72,
          'topic': '/rag_demo_smoke/chatter', 'published_count': len(published),
          'received_count': len(received), 'passed': bool(received and published),
          'listener_sample': received[:2]}
print(json.dumps(result, indent=2))
if not result['passed']:
    for output in outputs:
        print(output[-3000:])
    raise SystemExit(1)
PY
