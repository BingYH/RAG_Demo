"""Verify Windows -> WSL localhost HTTP, then stop the temporary Linux server.

Windows Python standard library only. No ROS, model calls or directory serving.
"""

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from http.client import HTTPException
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

LINUX_SERVER = r'''
import json, os, platform, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

port, run_id = int(sys.argv[1]), sys.argv[2]
if sys.platform != 'linux' or 'microsoft' not in platform.release().lower():
    raise SystemExit('This probe server requires WSL Linux.')
payload = {'service': 'rag-demo-http-probe', 'run_id': run_id,
           'source': 'wsl_linux_http', 'platform': sys.platform,
           'kernel': platform.release(), 'linux_pid': os.getpid(),
           'ros_connected': False, 'status': 'ok'}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/health':
            self.send_error(404)
            return
        raw = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)
    def do_POST(self):
        self.send_error(405)
    def log_message(self, *args):
        pass

server = HTTPServer(('127.0.0.1', port), Handler)
def stop_from_stdin():
    sys.stdin.readline()
    server.shutdown()
threading.Thread(target=stop_from_stdin, daemon=True).start()
timer = threading.Timer(25, server.shutdown)
timer.daemon = True
timer.start()
print(json.dumps({'event': 'ready', 'run_id': run_id, 'port': port}), flush=True)
try:
    server.serve_forever(poll_interval=0.1)
finally:
    timer.cancel()
    server.server_close()
    print(json.dumps({'event': 'stopped', 'run_id': run_id}), flush=True)
'''


def verify(port=8765, distro="Ubuntu-24.04", user="byhan"):
    if sys.platform != "win32":
        raise ValueError("Run this probe with Windows Python, not inside Ubuntu.")
    if not 1024 <= port <= 65535:
        raise ValueError("Use an unprivileged TCP port from 1024 to 65535.")
    run_id = uuid4().hex
    opener = build_opener(ProxyHandler({}))  # Local traffic must not use an external proxy.
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        ["wsl", "-d", distro, "--user", user, "--cd", "/tmp", "--", "python3", "-u", "-c",
         LINUX_SERVER, str(port), run_id], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    result = {"run_id": run_id, "verified_at": datetime.now(timezone.utc).isoformat(),
              "client_platform": sys.platform, "distro": distro, "endpoint": base + "/health",
              "passed": False, "server_stopped": False}
    try:
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
        event = json.loads(ready.get(timeout=15))
        if event != {"event": "ready", "run_id": run_id, "port": port}:
            raise RuntimeError("Unexpected readiness event.")
        last_error = None
        for _ in range(6):
            try:
                started = time.perf_counter()
                with opener.open(base + "/health", timeout=2) as response:
                    payload = json.loads(response.read(16384))
                    status = response.status
                result["round_trip_ms"] = round((time.perf_counter() - started) * 1000, 2)
                break
            except (URLError, TimeoutError, ConnectionError, HTTPException) as exc:
                last_error = exc
                time.sleep(.3)
        else:
            raise RuntimeError("Windows could not reach the WSL localhost endpoint.") from last_error
        if (status != 200 or payload.get("run_id") != run_id or payload.get("platform") != "linux"
                or payload.get("source") != "wsl_linux_http" or payload.get("ros_connected") is not False):
            raise RuntimeError("HTTP response did not identify the expected WSL probe.")
        result.update(http_status=status, server_response=payload)
        for name, request, expected in (
            ("unknown_path_status", Request(base + "/not-a-route"), 404),
            ("post_rejected_status", Request(base + "/health", data=b"", method="POST"), 405),
        ):
            try:
                with opener.open(request, timeout=2) as response:
                    observed = response.status
            except HTTPError as exc:
                observed = exc.code
                exc.close()
            if observed != expected:
                raise RuntimeError("Probe route boundary did not match expected behavior.")
            result[name] = observed
        result["passed"] = True
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = "Cross-system HTTP verification failed; inspect the distro, port and localhost forwarding."
    finally:
        try:
            if process.poll() is None:
                process.stdin.write("STOP\n")
                process.stdin.flush()
            output, error = process.communicate(timeout=8)
            stopped = any(line == json.dumps({"event": "stopped", "run_id": run_id}) for line in output.splitlines())
            result["server_stopped"] = process.returncode == 0 and stopped
            if not result["server_stopped"]:
                result["server_exit_code"] = process.returncode
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
            process.communicate(timeout=30)  # Linux watchdog also stops the listener after 25 seconds.
        result["passed"] = result["passed"] and result["server_stopped"]
    if result["server_stopped"]:
        try:
            with opener.open(base + "/health", timeout=1):
                result["endpoint_unreachable_after_stop"] = False
        except (URLError, TimeoutError, ConnectionError, HTTPException):
            result["endpoint_unreachable_after_stop"] = True
        result["passed"] = result["passed"] and result["endpoint_unreachable_after_stop"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--distro", default="Ubuntu-24.04")
    parser.add_argument("--user", default="byhan")
    args = parser.parse_args()
    result = verify(args.port, args.distro, args.user)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    directory = Path(__file__).resolve().parents[1] / "data/wsl_validation"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "http_smoke.json").write_text(text + "\n", encoding="utf-8")
    print(text)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
