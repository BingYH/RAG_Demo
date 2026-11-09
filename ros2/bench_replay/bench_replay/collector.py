import argparse
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from simulator.ros_capture import Capture, TOPIC


class Collector(Node):
    def __init__(self, port):
        super().__init__("bench_evidence_collector")
        self.capture = Capture()
        self.lock = threading.Lock()
        self.subscription = self.create_subscription(String, TOPIC, self.receive,
            QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE))
        collector = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with collector.lock:
                    capture = collector.capture
                    if self.path == "/health":
                        status, data = 200, {"service": "bench-ros-evidence", "source": "wsl_ros2_synthetic_replay",
                            "status": "error" if capture.error else "ready" if capture.frozen else "collecting",
                            "received_samples": len(capture.rows), "error": capture.error,
                            "capture_id": capture.begin["capture_id"] if capture.begin else None}
                    elif self.path == "/snapshot":
                        status, data = (200, copy.deepcopy(capture.frozen)) if capture.frozen else (
                            503, {"error": capture.error or "CAPTURE_NOT_COMPLETE"})
                    else:
                        status, data = 404, {"error": "NOT_FOUND"}
                raw = json.dumps(data, allow_nan=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                self.send_error(405)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.http_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.http_thread.start()

    def receive(self, message):
        with self.lock:
            try:
                self.capture.accept(json.loads(message.data))
            except (ValueError, TypeError):
                self.capture.error = "INVALID_OR_INCOMPLETE_ROS_CAPTURE"
                self.get_logger().error("Capture rejected; no diagnostic snapshot will be published.")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.http_thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    rclpy.init()
    node = Collector(args.port)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()
