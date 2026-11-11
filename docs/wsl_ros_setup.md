# WSL and ROS 2 environment

The goal is offline bench replay and delivery of ROS evidence to the AI workflow.
Installation does not establish hardware communication, robot control or real-time performance.

## Environment baseline

- Windows WSL `2.6.3.0`, distribution `Ubuntu-24.04`, WSL 2.
- Ubuntu Noble 24.04, ordinary user `byhan`, locale `C.UTF-8`.
- ROS 2 Jazzy `ros-base`, C++/Python demo nodes and `ros-dev-tools`.
- No Gazebo/full ROS desktop; Windows Streamlit/Claude remains separate.
- Passwords are not project configuration and must not enter scripts, files or traces.

## Installation and sources

`scripts/setup_ros_jazzy.sh` is for the selected Ubuntu 24.04 distribution and
runs as its root user. It verifies the distribution, configures the official
`ros2-apt-source`, then installs the base environment, tools and communication
examples through apt. It does not perform a full system upgrade; dependencies
may update relevant libraries.

References: [Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
and [official documentation source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst).

Windows Python can pass script contents through stdin to
`wsl -d Ubuntu-24.04 --user root --cd /tmp -- bash -s`, without a password.
Use only the authorized distribution; do not execute Linux installation commands
directly in PowerShell.

## Daily use

Enter Ubuntu from PowerShell:

~~~powershell
wsl -d Ubuntu-24.04 --cd /home/byhan
~~~

Load ROS in each new Ubuntu terminal:

~~~bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"
ros2 --help
~~~

The project does not automatically modify `.bashrc`. Use
`~/rag_demo_ros_ws` for Linux builds. Do not reuse Windows `.venv` as a Linux
environment or copy the entire reference repository directory into the workspace.

## Communication smoke test

`scripts/verify_ros_jazzy.sh` runs a C++ talker and Python listener as separate
ordinary-user processes. It uses isolated `ROS_DOMAIN_ID=72`, localhost discovery
and `/rag_demo_smoke/chatter`. It observes eight seconds, checks actual publishing/
receiving and stops only its own processes.

Run in Ubuntu:

~~~bash
bash /mnt/c/E/Workspace_BH/Tech_Review/RAG_Demo/scripts/verify_ros_jazzy.sh
~~~

No hardware, motion commands or model credits are involved. This verifies local
ROS communication, not cross-system DDS discovery or AI integration.

On 2026-11-09 installation/test passed as `byhan`, `ROS_DISTRO=jazzy`:
seven messages published and seven received in eight seconds, `passed=true`.
Processes exited. Results: ignored `data/wsl_validation/ros_jazzy_smoke.json`.
At that milestone, project-owned replay nodes had not yet been implemented.

## Windows → WSL HTTP verification

On 2026-11-09 Windows Python launched an ordinary-user WSL HTTP probe and requested
`http://127.0.0.1:8765/health`, receiving HTTP 200. Its random run ID matched
the launched Linux service; `platform=linux` and the WSL2 kernel confirmed the
response was not a Windows stub or stored JSON.

Unknown paths returned 404, POST returned 405. Only GET /health was exposed,
without directories. The service bound WSL 127.0.0.1; no firewall, port proxy
or .wslconfig changes were made. After shutdown, Windows received no HTTP response.
The first request took approximately 1037 ms, a cold-start observation rather
than a performance benchmark.

Reproduce from the project root in Windows PowerShell:

~~~powershell
.\.venv\Scripts\python.exe scripts/verify_wsl_http.py
~~~

This standard-library script defaults to Ubuntu-24.04, byhan and port 8765;
override with `--distro`, `--user`, `--port`. It starts, verifies and stops
the temporary service and writes `data/wsl_validation/http_smoke.json`.
Use another free port if occupied; do not stop unrelated services.
The service also exits automatically after 25 seconds.

This uses [WSL localhost networking](https://learn.microsoft.com/en-us/windows/wsl/networking#accessing-linux-networking-apps-from-windows-localhost).
It verifies Windows HTTP client → WSL service/response only, not ROS integration,
WSL → Windows service access or cross-system DDS discovery. The probe explicitly
reports `ros_connected=false`.

The next planned stage was trajectory replay and evidence collection, retaining
JSON offline mode. ROS messages must become frozen evidence with source, test/
snapshot IDs, time and missing-field explanations rather than an unbounded live
stream delivered directly to the model.

That stage is now implemented and all three replay conditions passed:
[ROS replay/bridge](ros_replay_bridge.md). The UI offers explicit Local JSON /
WSL ROS selection, retaining JSON mode: [Dashboard](dashboard.md).

Warnings about two old OpenCV Windows PATH entries are inherited path-conversion
warnings, unrelated to the ROS installation. The project leaves Windows PATH unchanged.
