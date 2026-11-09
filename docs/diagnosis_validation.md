# 终端诊断原型验证记录

验证日期：2026-11-07。模型：`claude-haiku-5-5`。知识版本：`37fe4f15f961fd0a`，五篇文档、25 个片段；本地 ONNX MiniLM + Chroma。此记录是开发验证，不是完整评估集或正确率承诺。

## 真实模型检查

| 场景 | 阅读回答后的观察 | Trace |
| --- | --- | --- |
| 连接超时 | 区分登记地址 .11 与配置地址 .12；远端版本保持未知；建议核实地址，没有宣布硬件损坏或修复成功 | [12 个步骤](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/df168f29-e4c9-4e0f-91d1-25524787fdc9/run/df168f29-e4c9-4e0f-91d1-25524787fdc9) |
| 版本不匹配 | 比较已观测协议 1 和客户端支持 [2]，指出本次握手不兼容；未执行升级或回滚 | [11 个步骤](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/9120bcd8-0c3d-4e34-9f3d-a65547b9b72e/run/9120bcd8-0c3d-4e34-9f3d-a65547b9b72e) |
| 正常快照 | 确认 diagnostic_ready，说明未采集 ROS 节点且不代表运动、安全或完整功能测试通过 | [12 个步骤](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/d6d56212-d166-40b2-b44e-46c5090cbaec/run/d6d56212-d166-40b2-b44e-46c5090cbaec) |

以上均通过 v2 API 查询确认模型、工具、检索与外层流程记录可见且已结束。链接需要该 LangSmith 工作区访问权限，并受平台保留周期限制；本地成功输出与用量见被 Git 忽略的 `data/runs/`。

## 验证中发现与修正的问题

- 首次回答被输出预算截断：提高预算并要求简洁输出；截断结果明确失败，不作为完成的诊断。
- 模型曾缩短日志证据 ID：加入完整后缀说明、引用 ID 校验和一次有界纠正；仍不合格时失败。
- LangSmith 返回了新的 `/trace/.../run/...` 链接格式：修正项目 ID 提取，只读回验原 Trace，未为此重新调用模型。
- 版本场景曾返回英文：后续提示词明确默认使用简体中文及中文标题。模型措辞仍有不确定性。

## 离线检查及限制

单元测试覆盖工具参数、状态隔离、文档范围、调用与引用边界；另对三个场景素材作一致性校验。实际向量查询已检查地址差异、版本兼容和 diagnostic_ready 边界等主题可命中相关文档。

引用 ID 有效不等于引用支持全部陈述，仍需人工或后续评估器检查。当前没有自动化语义评分、跨轮对话、LangGraph 状态恢复或工单创建。下一步应建立固定评估案例，再增加编排分支。

## 第二阶段：事实与来源绑定

同日将提示词升级为 `diagnosis-v2-bound-facts`。新增字段事实注册表与 Pydantic 结构化报告；模型通过 `submit_analysis` 选择事实 ID，程序直接生成事实名称、值与来源引用。登记与实际版本/地址配对显示，不允许模型自填事实值或引用 ID。完整字段路径、来源、快照和时间可在本地结果及工具 Trace 中查看。

离线测试增加了登记客户端 1.4.0 与实际安装 2.0.0、数值相同但来源不同、登记控制器版本已知而握手版本未知、伪造字段绑定、未返回文档引用和跨快照引用等案例。事实部分是确定性呈现；推断文字的语义不由这些校验保证。

真实模型复验：

- [超时场景](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/405a6ad3-3b33-4736-8273-d7c52f08f8a8/run/405a6ad3-3b33-4736-8273-d7c52f08f8a8)：事实部分按运行配置、资产登记和连接观察分别引用，12 个步骤已回读。
- [版本不匹配场景](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e20d65c0-abdd-430b-9683-fd2f8ce12f02/run/e20d65c0-abdd-430b-9683-fd2f8ce12f02)：实际客户端 2.0.0 引用 EV-026-02，期望版本 1.4.0 引用 EV-026-01，12 个步骤已回读。

首次复验中，模型提交的事实数量超出原报告容量，且纠正反馈不够具体；已扩大结构容量、要求精简选择并返回字段级验证反馈。另调高结构化输出预算，保留截断时明确失败的行为。

人工阅读仍发现模型解读把部署记录的 09:50 写成了 10:50；程序事实区原始记录保持 09:50。这说明字段绑定解决了事实区的来源错配，但没有解决模型在推断或建议中复述数据时的全部语义错误，后续评估应单独覆盖时间、版本等复述准确性。

## 第三阶段：解读与追问的证据复核

提示词升级为 `diagnosis-v3-evidence-review`。结构校验后增加单独的 `evidence_review` 模型请求，读取报告、字段事实和被引用的知识片段，检查网络过度结论、重复索要已知值、错误的兼容选项及明确的事实矛盾。结构、引用及语义问题共用一次纠正机会。用量包含生成与复核；复核器不执行业务操作。

- [完整版本场景验证](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/de82a51d-8cc0-4ec0-8cdd-30087036f009/run/de82a51d-8cc0-4ec0-8cdd-30087036f009)：13 个步骤已回读。回答没有询问已取得的控制器版本；描述 ping/握手证据的范围，建议依据文档评估 1.4.0／协议 1 基线，若保留 2.0.0 则核实协议 2 的控制器依据。
- [固定回归检查](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/4b9556d8-12c0-4b7b-8ee5-fd069660f315/run/4b9556d8-12c0-4b7b-8ee5-fd069660f315)：旧错误变体检出 `network_overclaim`、`redundant_question`、`compatibility_error`；合理变体通过。

首次回归检查漏掉了“问题句中的协议 1 或 2 配套选项”歧义；明确问题句也须满足协议约束后，两个变体复验通过。此结果只有一组正反例，不保证复核器对其他措辞或工况同样有效，也不证明全部引用语义正确。33 项离线测试覆盖了结构化复核、一次纠正、重复失败停止和合并用量等行为。

## 第四阶段：LangGraph 节点与持久化恢复

已实现 `bench-graph-v1`，入口与实际路由见 [工作流说明](langgraph_workflow.md)。原始工具循环继续保留为基线。

- [地址差异暂停](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/8b2dd7f2-31cf-4194-b9bd-0e4f54e28dfc/run/8b2dd7f2-31cf-4194-b9bd-0e4f54e28dfc)：经过证据收集、知识检索和覆盖检查，进入 clarify 中断。13 个执行步骤已回读，模型用量为零。
- [新进程恢复](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/edcb06d0-0c0f-48b3-9238-4e6b9c3bb075/run/edcb06d0-0c0f-48b3-9238-4e6b9c3bb075)：前一进程退出后，用“暂不清楚”的模拟回复恢复同一线程。12 个步骤已回读，继续生成、校验、复核并 finalize。
- 对比本地两个运行状态，原始 evidence、字段 facts 和检索 chunks 完全一致；collect_evidence / retrieve_knowledge 各只执行一次。用户说明只进入 user_context，没有变成实测版本或配置变更。
- [真实纠正分支](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/09f8a22c-a9b9-48a6-b9ab-1f241cc6916e/run/09f8a22c-a9b9-48a6-b9ab-1f241cc6916e)：版本场景首次复核检出网络过度结论，图进入 correct_report，再生成和复核后通过；30 个执行步骤已回读。

检索不足的一次重试、重试后转人工、结构纠正、重复复核失败、工具采集失败、旧文档排除、SQLite 关闭后重新建图恢复，以及恢复时版本漂移拒绝均有离线测试。实际检索重试路径只做了模拟模型测试，没有人为削弱真实索引来制造演示。当前没有工单创建或审批分支。

## 第五阶段：本地工单闭环

升级为 `bench-graph-v2-tickets`，新增显式 `--ticket` 请求，以及草稿、修改、确认、取消、幂等创建和已批准创建失败后的重试。旧版检查点不自动迁移。

CLI 演示验证（模拟人工操作，不代表真实设备操作授权）：

- [生成草稿并暂停](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/01f29d5c-e5e4-4cde-9378-7a66c395ae7b/run/01f29d5c-e5e4-4cde-9378-7a66c395ae7b)：显式请求工单后，首次检索未覆盖支持规程，实际触发 refine_query；补齐资料后完成诊断，生成 r1 并等待审批，29 个步骤已回读。
- [修改并重新等待批准](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/2bb95682-7ff8-4a6f-af17-5203ee13f142/run/2bb95682-7ff8-4a6f-af17-5203ee13f142)：加入明确的 Demo validation 备注，生成 r2，6 个步骤已回读。旧 r1 哈希确认被 CLI 拒绝。
- [确认并创建本地记录](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/7487670f-79b8-4022-8822-b88c5890a2d8/run/7487670f-79b8-4022-8822-b88c5890a2d8)：r2 精确哈希确认后创建 `DEMO-TKT-5e493b067c0f14eb8d982904`，6 个步骤已回读。再次确认返回同一 ID，修改和确认均未增加模型用量。

本地权威记录为 SQLite，JSON 为可恢复导出；未向外部支持系统发送数据。验证工单含“仅供演示验证、仍需工程师复核、未授权设备变更”的人工备注，诊断推断本身仍有模型复核的既有限制。

58 项离线测试通过，其中 13 项为工单专项：精确内容批准、旧批准失效、受保护字段、跨进程修改/重批、取消不创建、并发去重、导出失败修复、创建已提交但图检查点未保存时重试，以及证据不足时不收录未复核推断。首次测试发现 Windows 下 SQLite 连接未及时关闭，已改为显式关闭连接后导出，并复验通过。

## 第六阶段：关节响应任务接入

当前版本 `bench-graph-v3-motion`，显式任务 `joint_response` 使用三个运动只读工具、独立的 `demo-joint-response-v1` 索引与生成提示词。初始化默认入口保持原有任务和知识范围；旧版检查点不自动迁移。运动任务除文档角色外还校验必需的指标与排查章节，缺失时有限重试，不能靠一个高相似度片段直接放行。

2026-11-08 的真实 Claude/LangSmith 验证：

| 工况与运行 | 结果 | Trace |
| --- | --- | --- |
| 基准，线程 `motion-v3-baseline-final-1108` | 0% 超调、0.67 s 调节时间与末段误差均通过，限制为本次离线动作；没有重复追问负载 | [24 步回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/7f96be20-e67f-4394-9342-1d8a3b1d70b3/run/7f96be20-e67f-4394-9342-1d8a3b1d70b3) |
| 振荡，线程 `motion-v3-oscillation-1108` | 58.53% 超调与 2.56 s 调节时间超限；Kd 变更作为优先核查假设，没有判定唯一根因或执行调参 | [24 步回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/43ee6d3e-bddb-4000-8c05-07ff96a956b3/run/43ee6d3e-bddb-4000-8c05-07ff96a956b3) |
| 负载缺失，线程 `motion-v3-load-1108` 启动 | `check_evidence → clarify` 暂停，模型用量为零 | [16 步回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e24eefab-5640-4b01-ad47-a61271c1922e/run/e24eefab-5640-4b01-ad47-a61271c1922e) |
| 同线程新进程恢复 | 使用明确标为演示验证的“不清楚”回复，16.01% 超调/1.8 s 调节时间判失败，负载与惯量仍未知；生成含 TEST-307 的工单草稿，等待审批 | [15 步回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/121be7c7-79ed-4743-b5e0-f6d75a23243b/run/121be7c7-79ed-4743-b5e0-f6d75a23243b) |

本地对比恢复前后，`evidence`、`facts`、`chunks` 完全一致，收集与检索各只执行一次。用户回复仅存为未验证背景。草稿保留两个明确缺口：`payload_record` 与 `equivalent_inertia` 未采集。该真实测试线程停在审批，未自动批准或创建工单；运动工单审批后的创建通过离线 SQLite 测试验证，沿用原工单存储逻辑。

首次基准运行仍多问了已经记录完整的负载信息，复核当时没有检出。补充“离线条件完整时不虚构物理装配确认前置条件”的生成与评审规则后，上表最终基准运行不再追问。负载缺失报告保留未知事项，但图不会再次阻塞追问；未知根因并未被强行补齐。

固定正反例 `evaluation/cases/joint_response_review.json` 的真实复核结果：错误变体检出 `motion_overclaim` 与 `unsupported_claim`（登记惯量冒充当前值、PD 积分饱和、自动调参）；有边界的合理变体通过。[5 步回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/722687eb-bbed-41d0-b07d-2927a6f80bd5/run/722687eb-bbed-41d0-b07d-2927a6f80bd5)。可用 `python scripts/evaluate_review.py --case joint_response_review` 复现，使用模型 API 额度。场景标签与预期答案不送入复核请求。

75 项离线测试通过；新增运动图测试覆盖工具分流、错误知识范围/缺失要求章节拒绝、必需工具失败、SQLite 关闭后恢复且不重采、未知值不被人类回复覆盖、草稿保持缺口、批准后本地创建。原有初始化与工单测试、三个初始化素材校验继续通过。这是有限用例验证，复核仍可能漏检措辞、因果或引用问题，不保证任意输入的模型结果正确。
