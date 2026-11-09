# 关节响应案例：仿真与证据设计

状态：已完成三组正式 CSV/状态与响应图、两篇英文知识、三个会话只读工具和事实绑定，已接入 Claude/LangGraph，支持负载澄清与工单审批。三种工况均已真实运行并回读 LangSmith Trace。此文是实现依据，不进入 RAG；初始化与通信工作流继续保留。

## 1. 演示问题与范围

> 单关节位置跟踪测试出现超调。请检查本次测试条件、控制配置和响应结果，判断哪些指标不符合演示规程；证据不足时先澄清，必要时准备支持工单。

展示重点是 AI 如何关联测试要求、可读取证据和信息缺口。计算响应、计算指标和判定数值阈值由确定性代码完成；LLM 解释结果、提出有依据的假设并推进调查。

对象仍属于虚构 `BENCH-001 / DEMO-ARM-7`，但只建模一个抽象旋转关节 `DEMO-JOINT-01`，不指定它对应真实 Franka 的哪个关节。其余六轴不参与计算。使用离线模型，运行环境沿用 Windows Python；这一阶段不需要 ROS 2、Gazebo 或实体设备。

第一批采用 **PD 位置控制，积分项为零**。可以把它介绍为 PID 相关功能测试案例，但界面、配置和报告必须明确实际模式为 `PD`，不能称已实现完整 PID 控制器。

## 2. 公开背景与模型边界

本地公开参考为 `references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp`。其 `update()` 使用位置误差乘 `k_gains` 与负的滤波速度乘 `d_gains` 形成关节力矩，未包含积分项。该源码用于说明位置误差和速度阻尼的概念背景。

本项目独立设计下面的单关节模型、阶跃动作、参数、采样和验收阈值；不移植该控制器，不复现其滤波、参考轨迹或真实机器人动力学。正式知识材料引用该文件时须记录本地 commit 与文件 hash。

模型为：

```text
J × q_ddot + b × q_dot = torque
error = q_target - q
torque_requested = Kp × error - Kd × q_dot
torque = clamp(torque_requested, -torque_limit, torque_limit)
```

`q` 单位 rad，速度 rad/s，力矩 N·m；`J` 单位 kg·m²，`b` 和 `Kd` 单位 N·m·s/rad，`Kp` 单位 N·m/rad。速度反馈取模型速度，不对阶跃目标做差分。

这是理想化的惯量与粘性阻尼模型：不建模重力、轴间耦合、摩擦死区、齿隙、传感器噪声、通信延迟或执行器内部环。无噪声、无随机数，数值结果可重复。不能将模型的通过结论或参数用于实体机械臂。

## 3. 固定测试动作与计算约定

| 项目 | 约定 |
| --- | --- |
| 规程 / 模型 / 指标版本 | `DEMO-JOINT-STEP-001 v1` / `joint-inertia-pd-v1` / `joint-step-metrics-v1` |
| 初始位置、速度 | 0 rad、0 rad/s |
| 时间范围 | 0～6 s，包含两个端点 |
| 目标动作 | 前 0.5 s 保持 0 rad；从 0.5 s 起保持 0.2 rad，约 11.46° |
| 积分与控制周期 | 0.001 s；每步更新控制输出 |
| 输出采样周期 | 0.01 s，共 601 行；图与指标均使用这份采样数据 |
| 数值方法 | 半隐式 Euler：先由当前状态计算力矩与加速度，再更新速度，最后用新速度更新位置 |
| 力矩限幅 | ±2 N·m；记录请求值与限幅后的值 |
| 基准模型参数 | J = 0.05 kg·m²，b = 0.05 N·m·s/rad |
| 基准控制参数 | Kp = 4，Kd = 0.85，Ki = 0；实际模式 PD |

阶跃只用于离线特性演示，不是实体机器人运动指令。采用整数步号生成时间，避免浮点时间比较导致动作提前或延后一步。保存每个采样点当前的目标、状态及由该状态计算的控制输出，然后执行下一积分步。

## 4. 指标、要求与未知值

指标在阶跃开始后计算；阈值全部为项目自定义演示要求，绝非 Franka 或 Agile Robots 标准。

| 指标 | 定义 | 演示要求 |
| --- | --- | --- |
| 超调 `overshoot_pct` | `100 × max(0, max(q) - 0.2) / 0.2` | ≤5% |
| 调节时间 `settling_time_s` | 相对 0.5 s 的最早采样时刻，此后到记录末端所有位置均在目标 ±0.004 rad（阶跃幅值的 2%）内，且剩余观察至少 0.5 s | ≤1.5 s |
| 末段平均误差 `steady_state_error_rad` | 最后 0.5 s（5.5～6 s，含端点）内 `target - actual` 的算术平均；它是有限窗口估计 | 绝对值 ≤0.002 rad |
| 峰值误差 `peak_abs_error_rad` | 阶跃开始后 `max(abs(target - actual))` | 描述性指标，不单独判失败 |
| 输出限幅占比 `saturation_fraction` | 阶跃窗口内请求力矩绝对值大于力矩限制的采样点数 / 窗口采样点数 | 描述性指标，不单独判失败 |

若记录结束时仍不满足调节定义，`settling_time_s=null`，附 `not_settled_within_observation_window`；在本次观察窗口足够覆盖 1.5 s 限值的前提下，该项判为未通过。记录太短或损坏则为 `not_evaluable`，不能冒充已通过或明确测得某个调节时间。

每项结果保存 `metric_id`、计算值、单位、要求 ID、阈值、比较运算符、结果与计算窗口。指标关联轨迹 SHA256 和指标版本；知识库提供定义与要求，工具提供本次计算结果。模型不得自行补算或编造数值。

区分两个结论：`response_requirement_status` 表示这条记录的数值是否满足上述要求；`test_context_status` 表示测试条件是否完整、能否与基线比较。即使负载未知，仍可描述曲线超调与阈值比较，但不能宣称完成了有效的整机功能验收。

## 5. 三个首批工况

以下生成参数和预期行为仅供实现、评估，不进入模型上下文、工具响应或 RAG。

| 开发者场景名 | 生成条件 | 预期行为 |
| --- | --- | --- |
| `joint_tracking_baseline` | 基准 J、b、Kp、Kd；测试条件完整 | 报告本次单关节、此动作、此负载条件下指标通过；不扩大为整机正常 |
| `joint_tracking_oscillation` | J、b、Kp 不变；Kd 从登记基准 0.85 改成 0.10，有配置变更记录，负载信息完整 | 报告超调和调节时间超限；降低的速度阻尼是有依据的重点假设，建议工程师核对配置并受控复测；不自动调参 |
| `joint_tracking_load_unknown` | 控制配置保持基准；生成器 J = 0.20，b 不变；本次负载与等效惯量记录不提供给助手 | 指出曲线不符合要求且当前控制参数与基准一致；先补充工具/负载及条件变化记录，保留多种假设，不断言实际惯量增大或 PID 参数错误 |

正式 CSV 重算结果：基准超调 0%、调节时间 0.67 s；低阻尼约 58.53%、2.56 s；未知负载约 16.01%、1.80 s。生成器保存 CSV 后重新读取计算指标，检查器校验轨迹 hash 并重算结果；没有把这些近似数值写死成指标输出。

第三种工况中，隐藏的生成参数只属于生成器/评估侧。模型只收到 `payload_record=null`、`equivalent_inertia=null` 及 `not_collected` 原因；图标题、文件名、路径、日志、快照 ID、工单附件和 Trace 输入都不能泄露预设根因。基线登记值必须标明为登记信息，不能填补当前未知值。

## 6. 可读取证据与文件结构

三个运动证据接口已在 `simulator/motion_tools.py` 实现，CLI 可用 `--tool` 调用：

| 工具 | 返回内容 |
| --- | --- |
| `read_motion_test_conditions` | 测试编号、规程版本、关节、动作、时间窗口、采样周期、当前负载/夹具记录、参考基线及其登记来源、缺失项 |
| `read_control_configuration` | 本次模式、Kp/Ki/Kd、限幅、配置版本和变更记录；登记基准单独标记 |
| `read_motion_test_results` | 计算指标与要求比较、数据完整性、轨迹 ID/hash/采样数、模型与指标版本；不把完整 CSV 塞进模型上下文 |

输入只允许会话绑定的台架与测试 ID，不允许模型任意指定文件路径。延用现有证据包络、不可变快照、字段级事实绑定与未知值规则。确定性指标标记为派生证据，并记录输入轨迹和计算方法；不伪装为直接传感器测量。

拟采用目录：

```text
docs/joint_response_demo.md                  # 本设计，已建立
simulator/motion.py                         # 已实现：独立生成器、指标计算、校验与绘图
simulator/motion_scenarios/<scenario>/       # 已生成：state.json + trajectory.csv
scripts/generate_motion_fixtures.py          # 已实现：离线生成、校验
scripts/inspect_motion.py                    # 已实现：离线文件检查、工具调用与绘图入口
simulator/motion_tools.py                    # 已实现：会话绑定的三个只读工具与工具定义
knowledge/20_procedures/joint_response_test.md # 已完成
knowledge/30_troubleshooting/joint_response_anomalies.md # 已完成
evaluation/cases/joint_response_*.json        # 预期行为，与模型可见资料分离
data/motion_reports/                         # 生成的曲线与运行结果，忽略提交
```

CSV 至少包含 `time_s,target_position_rad,actual_position_rad,velocity_rad_s,requested_torque_nm,applied_torque_nm`。正式 fixture 的 CSV 与状态一同版本管理，运行导出的图放 `data/`。状态只保留可观察条件与结果，不包含生成器隐藏参数或预期根因。

首张图采用目标位置和实际位置随时间变化的两条曲线，并画出误差带、标注超调与观察窗口。图从同一 CSV 生成，显示“离线合成数据”；无需先做完整控制面板。

## 7. 接入现有 AI 工作流的方法

当前图以显式 `task_type` 选择初始化诊断或关节响应诊断，分别配置工具、知识范围和证据检查，复用报告校验、评审、一次纠正与工单审批。版本为 `bench-graph-v3-motion`；旧检查点不自动迁移。入口与命令见 [工作流说明](langgraph_workflow.md)。

关节响应路径：读取条件/配置/结果 → 检索试验规程与排障资料 → 检查证据 → 条件缺失则暂停澄清 → 生成有引用的解释 → 校验与评审 → 按请求准备工单并等待确认。

未知负载的追问应具体：本次使用了什么工具、负载是否更换、是否有对应记录。用户口述仍标为未验证上下文；不会修改原始快照或让旧指标自动变成新测试结果。用户不知道时可继续形成带缺口的报告/工单，不无限追问。

报告评审新增检查：把超调直接归因于 PID、将登记负载冒充本次负载、把单关节指标通过说成整机通过、捏造未测得的指标、要求自动执行参数调整。工单确认仍只授权本地工单创建。

## 8. 实施顺序与验收

1. 生成三组轨迹、计算指标，输出三张响应图；先离线确认普通观众能看懂差异。
2. 落实只读工具、事实字段和英文知识材料；确保隐藏生成参数不会进入模型或检索结果。
3. 在 LangGraph 中增加任务类型与运动证据检查，复用澄清、评审与工单闭环；更新工作流版本，避免旧检查点混用。
4. 分别验证基准不扩大结论、低阻尼有据但不武断、负载未知会追问/保留缺口，并在 LangSmith 检查分支与引用。

计算验收包括：同参数重复生成一致；CSV 行数/周期/单位正确；指标可从保存轨迹重算；无调节、短记录、缺失字段能被区分；三种响应在阈值两侧有足够余量。已有初始化与工单测试继续通过。

四项均已落实：三张图已目视检查；工具、事实绑定、知识范围隔离与检索已验证；图内任务分流、SQLite 澄清恢复、工单审批和证据评审可用。全部 75 项离线测试通过，三种工况真实运行与 Trace 验证见 [验证记录](diagnosis_validation.md)。当前不需要额外产品、机器人环境或内部资料。

## 9. 本地查看与重现

在项目根目录运行：

```powershell
# 重新生成三组版本化 fixture，并生成三张 PNG
.\.venv\Scripts\python.exe scripts/generate_motion_fixtures.py

# 校验保存数据、显示证据状态，并重画指定曲线（不调用模型/API）
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --plot

# 读取会话绑定的条件证据，未知负载保持 null
.\.venv\Scripts\python.exe scripts/inspect_motion.py --scenario joint_tracking_load_unknown --tool read_motion_test_conditions
```

知识检索使用 `KnowledgeIndex(applies_to="demo-joint-response-v1")`，两篇文档共 17 个片段；默认初始化索引仍为原来 5 篇、25 个片段。负载缺失查询命中排查文档，没有混入工况名称或预设答案。公开控制概念的源码 commit/hash 已加入来源 manifest（6 仓库、23 个文件）。三种工况已做端到端验证；这些有限案例不能保证模型对任意输入都正确。

图位于 `data/motion_reports/TEST-104.png`（基准）、`TEST-218.png`（低阻尼）、`TEST-307.png`（负载信息缺失）。开发者通过场景名选择输入，图与状态仅使用中性 ID。绘图依赖 Matplotlib，已加入 `requirements.txt`；没有模型调用费用。生成命令会覆盖上述三个合成 fixture，检查命令只读取 fixture 并可重画运行图。
