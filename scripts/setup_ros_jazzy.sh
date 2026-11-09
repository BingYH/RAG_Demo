#!/usr/bin/env bash
# Provision ROS 2 inside the explicitly selected Ubuntu-24.04 WSL distro.
# No credentials, Windows settings, hardware access or full-system upgrade.
set -euo pipefail
if [[ $(id -u) != 0 ]]; then
  echo 'Run as root inside the intended Ubuntu-24.04 distro.' >&2
  exit 1
fi
. /etc/os-release
if [[ ${ID} != ubuntu || ${VERSION_CODENAME} != noble ]]; then
  echo 'This setup requires Ubuntu Noble 24.04.' >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl python3
if ! dpkg-query -W -f='${Status}' ros2-apt-source 2>/dev/null | grep -q 'install ok installed'; then
  stage=$(mktemp -d /tmp/ros-jazzy-source.XXXXXX)
  trap 'rm -f -- "$stage/ros2-apt-source.deb" "$stage/release.json"; rmdir -- "$stage"' EXIT
  curl --fail --location --retry 2 https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest -o "$stage/release.json"
  release=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag_name"])' "$stage/release.json")
  if [[ ! $release =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo 'Unexpected source-package release version.' >&2
    exit 1
  fi
  curl --fail --location --retry 2 "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${release}/ros2-apt-source_${release}.noble_all.deb" -o "$stage/ros2-apt-source.deb"
  dpkg -i "$stage/ros2-apt-source.deb"
fi
apt-get update
apt-get install -y --no-install-recommends ros-jazzy-ros-base ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py ros-dev-tools
echo 'ROS_INSTALL_COMPLETE'
