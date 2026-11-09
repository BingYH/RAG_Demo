# ROS 轨迹回放与 HTTP 证据适配器

实现状态：项目自有 ROS 2 包已在 WSL 构建，三种工况均经过真实的 ROS 消息收发和 Windows HTTP 读取。Windows 只读会话适配器和 Streamlit 的本地 JSON / WSL ROS 选择已实现，界面真实英文诊断与草稿链路验证通过，见 [展示界面说明](dashboard.md)。终端 `graph_bench.py` 仍使用本地 JSON；ROS 命令用于回放/采集，不直接调用模型。

## 数据流

```text
WSL: 已有合成 CSV + 条件/配置
        ↓
bench_trajectory_replay 发布节点
        ↓ /rag_demo/motion_replay (std_msgs/String + 版本化 JSON)
bench_evidence_collector 订阅节点
        ↓ 收齐601点、校验序号/hash、重算指标、冻结
HTTP GET /snapshot (WSL 127.0.0.1:8765)
        ↓
Windows HttpMotionSession → 现有三个只读工具 / 字段事实注册表
```

这是离线合成数据在 ROS 中的回放，不是物理机械臂的新测量或重新运行控制器。采集结果标记 `source_type=synthetic`、`execution_mode=ros_synthetic_replay`，条件/配置的来源为 `ros_topic_observation`，指标为 `derived_calculation`。回放数据原始记录时间保存在 `fixture_observed_at`；`observed_at` 表示本次 ROS 采集完成时间，不改变合成数据的含义。

## 构建与运行

首次构建或修改共享模块/ROS 包后，在 Windows PowerShell 执行：

```powershell
wsl -d Ubuntu-24.04 --user byhan --cd /home/byhan -- bash /mnt/c/E/Workspace_BH/Tech_Review/RAG_Demo/scripts/build_ros_replay.sh
```

脚本将最小包、标准库共享模块与三个合成 fixture 复制到 `~/rag_demo_ros_ws/src/bench_replay`，使用 colcon 构建；不复制知识库、密钥、Windows 虚拟环境或外部参考仓库。不修改用户 `.bashrc`。

在项目根目录启动一条回放并保留 HTTP 服务：

```powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation
```

约六秒完成样本回放后，终端显示 capture ID、全新的测试编号、601点计数、响应结果和上下文完整性。保持这个终端运行。在另一个 PowerShell 中读取证据：

输出明确区分：`DATA CAPTURE: SUCCESS` / `capture_status=success` 表示 ROS→HTTP→Windows 的采集与校验成功；`response_requirement_status=fail` / `RESPONSE EVALUATION: FAIL` 表示记录的运动不符合演示要求，两者可以同时出现。结束时 `SERVICE STATUS: stopped` 表示已清理服务，`RUN STATUS: SUCCESS` 表示程序流程正常。退出码0不代表运动合格。已将原先容易混淆的 `response_status` 和 `BRIDGE_STOPPED` 输出替换为上述明确名称。

```powershell
.\.venv\Scripts\python.exe scripts/inspect_ros_motion.py --tool read_motion_test_results
.\.venv\Scripts\python.exe scripts/inspect_ros_motion.py --tool read_motion_test_conditions
```

可附加 `--capture-id` 核对刚才启动的回放身份。桥接器终端按 `Ctrl+C` 会停止它创建的两个节点及 HTTP 服务；不会停止其他 ROS 进程。只做自动验证并退出：

```powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_load_unknown --verify-only
```

三个场景名称与原有模拟器相同。开发者在命令行选择工况，ROS 消息和证据不携带该名称或预期根因。HTTP 默认端口 8765，可通过 `--port` 更改；采集工具要使用相同端口。该首版使用固定 `ROS_DOMAIN_ID=73`、仅 localhost 的发现范围和固定话题，同一时刻只运行一组桥接节点。

## 一致性与失败处理

- 发布端只读取已验证的 fixture，等待发现订阅端后发送 begin、601 个带连续序号的 sample 和 end。采集端本身不读取 fixture，不复制预存指标。
- 订阅端检查同一 capture ID、连续序号、样本数和轨迹 SHA256，再从收到的轨迹重算指标，并检查条件/配置与轨迹是否匹配。
- ROS 使用可靠 QoS、队列深度1000。可靠策略不能代替应用层完整性检查；缺样、重复、乱序、混合 capture 或错误 hash 都拒绝生成快照。
- 回放开始但未完整结束时 `/snapshot` 返回 HTTP 503；校验失败同样不返回合格快照。`/health` 单独报告 collecting / ready / error。未知路径404，POST405，无文件目录或控制接口。
- 每次成功采集生成新的中性 snapshot/test/evidence ID。快照冻结后再读 `/snapshot` 内容不变，不会因另一次 HTTP 请求或新消息改变已确定的案件。
- Windows 客户端一次获取完整快照和轨迹，限制响应大小、检查身份、重算指标与 hash，再绑定当前会话。之后各工具只读内存深拷贝，服务断开也不会替换该会话证据；新建客户端在服务不可用或证据无效时明确失败，绝不自动退回 JSON。
- `transport` 保留 capture ID、话题、采样数、序号验证、原始测试引用、源轨迹 hash 与采集完成时间，字段事实也保留此来源。它记录本地受信采集链，不构成远端设备身份认证。

## 2026-11-09 验证

| 回放 | Windows 校验采样数 | 重算超调 | 结果 | 条件 |
| --- | --- | --- | --- | --- |
| 基准 | 601 | 0% | pass | complete |
| 振荡 | 601 | 58.53% | fail | complete |
| 负载缺失 | 601 | 16.01% | fail | incomplete，负载与惯量仍为 null |

三种真实回放均已退出；本地输出保存在忽略目录 `data/wsl_validation/ros-capture-<id>.json`。另行验证了重复 HTTP 请求字节一致、停止服务后新客户端失败，以及真实 ROS 采集会话可直接作为 `build_workflow(session=...)` 的输入：负载缺失时图进入 `awaiting_input`、模型用量为零，事实保留同一 capture 来源。

测试中发现 rclpy 信号处理与主动 shutdown 存在竞争，已改用 `try_shutdown()`，并重新构建/验证干净退出。83 项离线测试覆盖原有功能及采集异常、指标篡改、固定快照和不回退行为。

ROS 开发参考 [官方 Python 发布/订阅教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html) 与 [QoS 说明](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)。目前使用标准 String 消息承载明确 JSON 契约，尚未定义自有 `.msg`、录制 rosbag、引入 Gazebo 或验证控制实时性。
