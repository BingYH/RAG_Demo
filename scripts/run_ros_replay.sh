#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/rag_demo_ros_ws/install/setup.bash"
export ROS_DOMAIN_ID=73
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONUNBUFFERED=1
exec python3 -m bench_replay.runtime "$@"
