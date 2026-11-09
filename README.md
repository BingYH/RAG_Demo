# RAG & AI Workflow Demo

面向机械臂测试台架技术支持的 AI 工作流演示：从有依据的知识问答，推进到诊断信息收集、人工确认和支持工单创建。

## 技术方向

- **RAG**：检索公开资料与合成知识文档，为回答提供可核查依据。
- **LangGraph**：管理状态、条件分支、有限重试和人工确认。
- **LangSmith**：追踪执行过程，通过固定案例评估工作流质量。

## 当前状态

本地 Streamlit 展示界面支持中文 / English、曲线与证据、澄清恢复、工单修改/审批及 Trace 查看。运行 `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py`，打开 `http://127.0.0.1:8501`。英文面试演示请先选 English，再开始新会话；已有记录保留原文。使用及验证见 [展示界面说明](docs/dashboard.md)。

已实现最小 Claude → LangSmith 验证、终端诊断基线、LangGraph 检索/纠正与 SQLite 恢复、本地工单草稿/审批/幂等创建和双语 Streamlit 界面；尚未接入外部工单系统。完整设计见 [演示计划](RAG_DEMO_PLAN.md)。

当前使用模拟诊断工具与本地工单记录，不依赖实体机械臂或完整 ROS 2 环境。

WSL 2 / Ubuntu 24.04 的 ROS 2 Jazzy 环境、轨迹回放、订阅采集与 Windows HTTP 只读适配器已实现，三种工况均完成601点真实收发验证。展示界面可显式选择本地 JSON / WSL ROS，已验证真实 ROS 快照到英文诊断、澄清和待审批工单；离线恢复保留原来源，不自动回退。使用步骤见 [展示界面](docs/dashboard.md)、[ROS 桥接](docs/ros_replay_bridge.md) 和 [WSL 环境](docs/wsl_ros_setup.md)。

Windows → WSL 的 localhost HTTP 链路已实际验证。`python scripts/verify_wsl_http.py` 只验证临时探针；`python scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation --verify-only` 则会启动真实 ROS 回放、获取重算后的证据并关闭节点，不调用模型。

关节响应扩展已接入 Claude/LangGraph：三组离线 PD 工况、独立知识检索、只读证据、负载澄清、报告评审和工单审批。模型与查看命令见 [关节响应案例](docs/joint_response_demo.md)，任务分流与恢复见 [工作流说明](docs/langgraph_workflow.md)。运行 `.\.venv\Scripts\python.exe scripts/generate_motion_fixtures.py` 可重现轨迹与曲线，PNG 输出到 `data/motion_reports/`。

```powershell
# 振荡工况，完成诊断
.\.venv\Scripts\python.exe scripts/graph_bench.py --task joint_response --scenario joint_tracking_oscillation

# 负载缺失，先澄清再准备工单；按终端提示恢复与审批
.\.venv\Scripts\python.exe scripts/graph_bench.py --task joint_response --scenario joint_tracking_load_unknown --ticket
```

当前工作流为 `bench-graph-v3-motion`；旧检查点需新开线程。初始化命令保持原有用法。

## 参考资料

本地仓库的用途、阅读顺序和来源映射见 [资料索引](docs/sources.md)，确切仓库版本与文件指纹见 [来源快照](docs/source_manifest.json)。参考仓库本身不提交到本项目。

模拟台架的组成、只读工具字段、三个初始场景与工单边界见 [台架定义](docs/demo_bench.md)。

第一批英文知识已写入 `knowledge/` 的五个主题目录；三个合成状态、日志及五个本地只读工具见 [模拟素材与工具说明](simulator/README.md)。执行 `python scripts/validate_fixtures.py` 可离线检查素材一致性。

例如，离线查看连接观察结果：

```powershell
python scripts/inspect_bench.py --scenario connection_timeout --tool read_connection_observations
```

## 数据与配置

演示采用公开资料和完全合成的案例，不包含雇主或客户的内部文档、日志和代码。公开来源与合成内容应分别标注。

API 密钥通过环境变量配置，不提交至 Git。虚拟环境、本地数据库、运行日志和外部参考仓库由 `.gitignore` 排除。

## 最小 Trace 验证（Windows PowerShell）

使用 Python 3.12，在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/smoke_trace.py
```

提前配置 `ANTHROPIC_API_KEY`、`LANGSMITH_API_KEY`、`LANGSMITH_TRACING=true` 和欧洲区 `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`。脚本优先读取进程环境；Windows 下缺失项会从当前用户环境变量补读，不打印密钥。

默认模型为 `claude-haiku-5-5`，可通过 `ANTHROPIC_MODEL` 修改。默认追踪项目为 `rag-demo-smoke`；如已配置 Agent ID，则使用对应的 Agent 配置。每次运行会产生一次收费模型调用，并把固定合成提示词与回答上传到 LangSmith。

成功时显示 `TRACE_OK`、Token 用量、`TRACE_VERIFIED` 和 Trace 链接。打开链接可查看外层 `claude-smoke-test` 与内层 Claude 调用的输入、输出、耗时和用量。脚本会回读远端记录，确认外层记录和模型子调用均可见。

## 知识与工具诊断闭环

以下 `diagnose_bench.py` 保留为原始工具循环基线。要体验 LangGraph 节点和暂停恢复，优先使用 [LangGraph 工作流说明](docs/langgraph_workflow.md) 中的 `graph_bench.py`：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario version_mismatch
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario connection_timeout
```

第二个场景遇到地址差异时暂停并显示恢复命令；使用同一 Thread ID 和 `--reply` 提供说明后继续。SQLite 状态保存于 `data/checkpoints/`，无需购买云部署服务。

体验完整工单闭环：

```powershell
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario version_mismatch --ticket
```

诊断后会显示完整草稿和 Approve / Edit / Cancel 命令。确认绑定当前草稿哈希，修改后需重新确认；创建结果保存在 `data/tickets/`，不会发送外部系统。字段修改、重复确认与失败恢复说明见 [本地工单闭环](docs/ticket_workflow.md)。

在项目根目录的 PowerShell 中更新依赖，然后运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario connection_timeout
```

Claude 自行选择五个只读诊断工具和 `search_knowledge`，再调用 `submit_analysis` 提交结构化报告。事实部分由程序按原始字段生成，Claude 选择事实 ID 并撰写解读、未知项和建议。终端先显示工具名，再显示回答、总 Token 用量和 LangSmith 链接。`submit_analysis` 只提交诊断报告，不创建工单。Trace 包含模型调用、工具输入输出、绑定的事实和检索片段；诊断脚本通过 LangSmith v2 API 回读执行步骤。

其他运行方式：

```powershell
# 只构建并查询知识索引，不调用 Claude 或 LangSmith
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --index-only

# 版本不匹配场景
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario version_mismatch

# 正常快照；自定义提问
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario healthy --question "请检查当前初始化状态，说明能确认和不能确认的内容。"
```

### 本地检索与运行边界

- Chroma 在 `data/index/` 保存向量索引；Embedding 使用 CPU 上运行的 `all-MiniLM-L6-v2` ONNX 模型。首次运行下载约 80 MB 模型到 `data/models/`，后续复用，不产生 Embedding API 费用。
- 仅索引 `knowledge/` 下状态为 current、适用于 demo-bench-v1 的文档；`archived/`、参考仓库、场景、设计文档和评估答案不进入索引。按章节分片，保留版本、来源 ID 和相对路径；内容变更自动使用新版本索引。
- 文档为英文，Claude 使用英文查询，默认用简体中文解释。余弦距离只表示候选排序，不表示结论正确或资料一定充分。
- 场景由命令行选择，不出现在模型可用参数中。一次运行绑定一个不可变快照；不是实时采集或真正复测。
- 最多 6 轮诊断生成请求、20 次工具调用（含报告提交）；结构、引用或证据复核不合格时共用一次纠正机会。另有最多 2 次模型复核请求；超限、截断或仍不合格的结果明确失败。
- 每条事实绑定 `tool`、字段路径、原值、登记/运行观察来源、证据 ID、快照及观察时间。Claude 不能提交事实名称、数值或证据 ID；最终事实行从绑定记录生成。选中版本或地址时自动展示登记与实际值两侧，防止相同值被合并或期望值冒充当前值。
- 报告提交通过 Pydantic 校验；不存在的事实、未取得的知识片段、混合快照和手写引用被拒绝。模型解读的引用按事实 ID 映射到证据 ID 后自动添加；这能保证来源映射存在，不能证明推断语义正确，仍需后续评估。
- 结构校验后新增 `evidence_review`：用独立模型请求对照事实和所引用文档，检查网络结论过度、重复追问已知值、兼容建议错误及其他明确矛盾。失败时返回具体问题供一次纠正；复核器自身格式错误则明确失败。模型复核仍可能漏报或误报，不是正确性保证。
- 每次诊断会多次调用收费模型，包括证据复核；`Usage` 汇总生成与复核的输入输出 Token。成功回答、工具调用摘要、复核意见和用量保存在被 Git 忽略的 `data/runs/`。Trace 中也可查看 `evidence_review` 及其模型子调用。
- 基线入口仍为单轮诊断；LangGraph 入口支持澄清与工单审批、跨进程恢复、精确内容确认和幂等本地创建。使用 --ticket 显式请求工单；不加则仅诊断。

### 离线验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_fixtures.py
```

单元测试使用假模型，不访问 API；覆盖工具边界、会话隔离、文档筛选、工具结果回传、字段来源绑定、结构化报告纠正与调用预算。首次本地 Embedding 模型下载及真实模型端到端检查不属于单元测试。

固定的证据复核回归案例位于 `evaluation/cases/version_mismatch_review.json`，包含旧错误和合理回答两个变体，均不进入 RAG。可执行以下收费模型检查：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_review.py
```

脚本分别调用复核器，检查旧回答是否被标记为网络过度结论、重复追问和兼容性错误，以及合理回答能否通过。预期标签不发送给复核模型；结果保存在 `evaluation/results/`。通过两个例子仅代表本次回归通过，不代表完整评估集上的准确率。
