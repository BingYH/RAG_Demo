# 模拟状态素材（v1）

这里包含诊断素材和已实现的本地只读工具；已通过基线脚本和 `scripts/graph_bench.py` 接入 Claude、知识检索与 LangGraph，没有独立网络服务。三个场景各含 `state.json` 和 JSON Lines 格式的 `diagnostic.log`；内容全部为英文合成数据，不来自真实设备或内部项目。

## 数据读取约定

- `state.json` 中 `observations` 的四个键对应四个状态读取工具；每个值已使用 `docs/demo_bench.md` 定义的证据包络。
- `log_stream` 保存日志工具的证据包络，不包含 `data`。读取工具从 `diagnostic.log` 取最后 N 条事件（默认 20，允许 1～100），按时间升序放入 `data.events`。
- `log_stream.evidence_id` 是原始日志流 ID。日志工具的响应证据 ID 使用 `<stream_id>-n<N>`，使不同 limit 的返回可区分；同一 limit 可复现。
- 工具通过会话绑定选择 fixture，模型不能提交路径或场景名。只返回所请求工具的包络，不返回整个 state 文件、目录名或 README。
- 运行配置使用 `execution_mode=fixture`；这是项目自建模拟，不等于启动了 ROS 2 fake hardware。
- `snapshot_at` 是历史回放参考时点。登记值的时间早于启动尝试；网络、握手、初始化和日志时间相互对应。
- 资产登记中的软件为期望基线，不代表当前远端值。未知值及原因保留在 `unavailable_fields`。
- fixture 不包括标准答案或根因字段；不纳入 RAG 索引。场景含义见设计文档，预期行为后续由 `evaluation/cases/` 独立定义。

## 三个目录

| 目录 | 素材范围 |
| --- | --- |
| `healthy/` | 基准软件、连接、握手及诊断状态记录 |
| `version_mismatch/` | 更新后的客户端、握手返回的版本/协议和拒绝事件 |
| `connection_timeout/` | 已加载配置、登记信息、端点超时与无法取得的远端状态 |

第一版不会根据助手建议修改 fixture，重复读取不代表真实重试或修复。`ros2_nodes=null` 表示未采集，没有运行 ROS 2 或机械臂。

在项目根目录执行 `python scripts/validate_fixtures.py`，可离线检查证据标识、时间顺序、未知字段、协议关系及日志与状态的一致性。`diagnostic.log` 是可提交的合成输入，已对通用 `*.log` 忽略规则添加精确例外；真实运行日志仍应放在 `logs/`。

## 使用只读工具

在项目根目录直接查看一个响应，无需 API Key 或第三方依赖：

```powershell
python scripts/inspect_bench.py --scenario connection_timeout --tool read_connection_observations
python scripts/inspect_bench.py --scenario version_mismatch --tool read_runtime_config
python scripts/inspect_bench.py --scenario healthy --tool read_diagnostic_log --limit 3
```

程序接入：

```python
from simulator.tools import DiagnosticSession, tool_specs

# 场景由应用选择；每个工作流会话保留一个实例。
session = DiagnosticSession("connection_timeout")
definitions = tool_specs()  # 可提供给 Claude 的五个工具定义
result = session.call("read_connection_observations", {"bench_id": "BENCH-001"})
```

会话在创建时一次性读取并保留素材；工具返回深拷贝，调用者不能通过修改响应影响后续结果。模型只能使用 `bench_id` 和日志工具的 `limit`，不能选择场景、路径或任意工具。无效请求返回 `status=error` 和错误码；加载损坏或缺失素材时，会话创建失败，返回不含本地路径的异常消息。

执行 `python -m unittest discover -s tests -v`，检查工具参数边界、未知值、快照隔离、日志截取和响应的数据边界。CLI 的退出码只表示工具是否执行成功；成功读取到故障证据仍返回退出码 0。

## 单关节响应只读工具

运动扩展与初始化工具分开，使用 `simulator.motion_tools.MotionSession`。三个工具为 `read_motion_test_conditions`、`read_control_configuration`、`read_motion_test_results`。构造时校验 CSV hash、重算指标并检查包络；调用时只读取固定快照，不重跑仿真，不访问文件或设备。

```powershell
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --tool read_motion_test_conditions
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_oscillation --tool read_motion_test_results
```

```python
from simulator.motion_tools import MotionSession, tool_specs

session = MotionSession("joint_tracking_load_unknown")  # 应用侧选择，不提供给模型
definitions = tool_specs()
result = session.call("read_motion_test_conditions", {
    "bench_id": "BENCH-001", "test_id": session.test_id,
})
```

工具定义要求 `bench_id` 和 `test_id`，禁止额外参数；不允许跨测试读取、任意路径或参数修改。CLI 默认用绑定的测试编号，也可用 `--test-id` 验证错误输入。返回值为深拷贝。当前未知负载与惯量保持 null 和 `not_collected`，登记基准不替代它们。`status=ok` 与指标通过是两回事。

`rag_demo.facts.extract_facts()` 已支持三个运动工具，指标按 `metric_id` 绑定而非列表位置；事实保留单位、阈值、判定和计算来源，登记字段标记 `asset_registry`。知识材料使用 `demo-joint-response-v1` 范围；`KnowledgeIndex(applies_to="demo-joint-response-v1")` 建立独立的内容版本索引。默认 `demo-bench-v1` 仍只检索原来五篇初始化材料。运动工具已通过显式 `--task joint_response` 接入 Claude/LangGraph，见 [工作流说明](../docs/langgraph_workflow.md)。
