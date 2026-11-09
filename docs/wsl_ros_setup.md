# WSL 与 ROS 2 环境

目标是运行离线台架状态回放节点，并将 ROS 证据送入现有 AI 工作流。环境安装不代表机械臂控制、真实硬件通信或实时性能验证。

## 环境基线

- Windows 已有 WSL `2.6.3.0`，发行版为 `Ubuntu-24.04`，运行模式为 WSL 2。
- Ubuntu Noble 24.04，普通用户为 `byhan`，locale 为 `C.UTF-8`。
- 选择 ROS 2 Jazzy 的 `ros-base`、C++/Python demo nodes 和 `ros-dev-tools`。
- 不安装 Gazebo 或完整 ROS desktop；Windows 中的 Streamlit/Claude 环境保持独立。
- 密码不属于项目配置，不写入脚本、文件或 Trace。

## 安装与来源

安装脚本为 `scripts/setup_ros_jazzy.sh`，只用于选定的 Ubuntu 24.04，须以该发行版的 root 执行。脚本检查发行版，使用官方 `ros2-apt-source` 配置 ROS 软件源，再通过 apt 安装基础环境、开发工具和通信示例。不会做全系统升级；apt 会按依赖需要更新相关系统库。

参考 [ROS 2 Jazzy Ubuntu 安装说明](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) 和其 [官方文档源码](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)。

脚本可通过 Windows 侧 Python 将文件内容作为 stdin 传给 `wsl -d Ubuntu-24.04 --user root --cd /tmp -- bash -s`，不需要传递密码。只在已授权配置的发行版中执行，不在 Windows PowerShell 里直接运行 Linux 安装命令。

## 日常使用

PowerShell 中进入普通用户的 Ubuntu：

```powershell
wsl -d Ubuntu-24.04 --cd /home/byhan
```

每个新的 Ubuntu 终端先加载环境：

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"
ros2 --help
```

目前未自动修改 `.bashrc`。Linux 侧后续构建工作区建议使用 `~/rag_demo_ros_ws`；不要把 Windows `.venv` 当作 Linux Python 环境使用，也不要直接将整个参考仓库目录复制进工作区。

## 通信验证

`scripts/verify_ros_jazzy.sh` 以普通用户运行两个独立进程：C++ talker 和 Python listener。使用隔离的 `ROS_DOMAIN_ID=72`、仅 localhost 发现范围和 `/rag_demo_smoke/chatter` 话题。观察 8 秒，检查实际发布与接收，再停止本脚本创建的进程。

可在 Ubuntu 中运行项目的校验脚本：

```bash
bash /mnt/c/E/Workspace_BH/Tech_Review/RAG_Demo/scripts/verify_ros_jazzy.sh
```

校验不启动真实设备、不发运动命令、不消耗模型 API 额度。结果用于确认本机 ROS 基础通信，而不是 Windows 与 WSL 的跨系统 ROS 发现或 AI 接入。

2026-11-09 实际安装和校验已完成：以 `byhan` 运行，`ROS_DISTRO=jazzy`，8 秒观察内发布 7 条、接收 7 条，`passed=true`；测试进程已退出。结果保存在本地忽略目录 `data/wsl_validation/ros_jazzy_smoke.json`。此时尚未实现项目自己的 ROS 台架回放节点。

## 下一步范围

### Windows → WSL HTTP 链路已验证

2026-11-09，使用 Windows Python 启动 WSL 普通用户的临时 HTTP 探针，并由 Windows 请求 `http://127.0.0.1:8765/health`，返回 HTTP 200。响应含本次随机运行标识、`platform=linux` 与 WSL2 kernel，标识与启动的 Linux 服务一致；不是 Windows 模拟返回或预存 JSON。

已验证：未知路径返回 404，POST 返回 405；服务仅提供 GET `/health`，不开放目录。探针仅监听 WSL 的 `127.0.0.1`，没有改防火墙、端口代理或 `.wslconfig`。测试结束后服务已停止，Windows 再次请求不再取得 HTTP 响应。第一次跨系统请求耗时约 1037 ms，仅为冷启动连接观察，不作为性能基准。

在 **Windows PowerShell** 的项目根目录复现：

```powershell
.\.venv\Scripts\python.exe scripts/verify_wsl_http.py
```

脚本使用标准库，默认发行版 `Ubuntu-24.04`、普通用户 `byhan`、端口 8765，可分别通过 `--distro`、`--user`、`--port` 指定。脚本会启动、验证并关闭临时服务，结果保存到 `data/wsl_validation/http_smoke.json`。若默认端口已有服务，改用空闲端口，不停止其他服务。服务还带 25 秒自动退出限制。

这一机制采用 WSL 的 localhost 访问能力，见 [Microsoft 官方网络说明](https://learn.microsoft.com/en-us/windows/wsl/networking#accessing-linux-networking-apps-from-windows-localhost)。当前验证范围是 Windows HTTP 客户端 → WSL HTTP 服务及其响应；不等于 ROS 数据已接入、WSL 能访问 Windows 服务或直接跨系统 DDS 发现已验证。响应中明确 `ros_connected=false`。

环境通过验证后，再实现台架轨迹回放节点与证据采集适配器，保留已有 JSON 模式作为离线备份。ROS 消息必须转成带来源、测试/快照 ID、时间与缺失字段说明的证据快照，不能让模型直接订阅一段未固定的状态流。

后续进展：上述回放、采集与 Windows HTTP 会话适配器现已实现，三个工况真实验证通过，见 [ROS 回放与证据桥接](ros_replay_bridge.md)。展示界面现可显式选择本地 JSON / WSL ROS，原有 JSON 继续保留，见 [界面说明](dashboard.md)。

WSL 启动时若提示两个旧 OpenCV Windows PATH 条目无法转换，这是继承的 Windows 路径告警；与本次 ROS 安装目录无关。暂不修改用户 Windows PATH。
