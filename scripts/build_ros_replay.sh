#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
project=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
workspace="$HOME/rag_demo_ros_ws"
package="$workspace/src/bench_replay"
mkdir -p "$package" "$package/simulator" "$package/fixtures"
cp -a "$project/ros2/bench_replay/." "$package/"
for module in __init__.py motion.py motion_tools.py ros_capture.py; do
  cp "$project/simulator/$module" "$package/simulator/$module"
done
for scenario in joint_tracking_baseline joint_tracking_oscillation joint_tracking_load_unknown; do
  mkdir -p "$package/fixtures/$scenario"
  cp "$project/simulator/motion_scenarios/$scenario/state.json" "$package/fixtures/$scenario/"
  cp "$project/simulator/motion_scenarios/$scenario/trajectory.csv" "$package/fixtures/$scenario/"
done
cd "$workspace"
colcon build --packages-select bench_replay --event-handlers console_direct+
echo ROS_REPLAY_BUILD_COMPLETE
