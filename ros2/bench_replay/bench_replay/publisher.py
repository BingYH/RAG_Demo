import argparse
import json
import time
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from simulator.motion import SCENARIOS, verify_fixture
from simulator.motion_tools import MotionSession
from simulator.ros_capture import TOPIC


class Replay(Node):
    def __init__(self, scenario, capture_id):
        super().__init__("bench_trajectory_replay")
        state, self.rows = verify_fixture(Path(get_package_share_directory("bench_replay")) / "fixtures" / scenario)
        MotionSession._validate(state, self.rows)
        obs = state["observations"]
        self.capture_id, self.index, self.started = capture_id, -1, False
        self.begin = {"kind": "begin", "capture_id": capture_id, "expected_samples": 601,
            "conditions": obs["read_motion_test_conditions"]["data"],
            "configuration": obs["read_control_configuration"]["data"],
            "unavailable_fields": obs["read_motion_test_conditions"]["unavailable_fields"],
            "trajectory_sha256": obs["read_motion_test_results"]["data"]["trajectory_sha256"],
            "model_version": obs["read_motion_test_results"]["data"]["model_version"],
            "fixture_observed_at": obs["read_motion_test_conditions"]["observed_at"]}
        self.pub = self.create_publisher(String, TOPIC, QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE))
        self.timer = self.create_timer(.01, self.tick)
        self.deadline = time.monotonic() + 30

    def tick(self):
        if not self.started:
            if not self.pub.get_subscription_count():
                if time.monotonic() > self.deadline:
                    raise RuntimeError("No replay subscriber discovered.")
                return
            message = self.begin
            self.started = True
        elif self.index < len(self.rows):
            message = {"kind": "sample", "capture_id": self.capture_id,
                       "sequence": self.index, "row": self.rows[self.index]}
        else:
            message = {"kind": "end", "capture_id": self.capture_id, "sample_count": len(self.rows),
                       "trajectory_sha256": self.begin["trajectory_sha256"]}
            self.timer.cancel()
        self.pub.publish(String(data=json.dumps(message, allow_nan=False)))
        self.index += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--capture-id", required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Replay(args.scenario, args.capture_id)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
