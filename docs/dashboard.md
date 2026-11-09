# 展示界面：本地运行与中英文演示

入口为 `streamlit_app.py`，复用现有 LangGraph 和 `data/checkpoints/diagnosis.sqlite3`。终端创建的当前版本会话可以粘贴 Thread ID 载入；页面刷新、查看曲线和切换语言不调用模型。

## 启动

在项目根目录的普通 PowerShell 中运行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

浏览器打开 `http://127.0.0.1:8501`。服务只监听本机，未部署到公网。需要服务进程能访问 Claude 和 LangSmith；不要在禁止出站网络的沙箱内启动。先前的 `APIConnectionError` 已确认由启动进程的网络限制引起，不是额度耗尽。API Key 仍从既有本地环境变量读取，页面不展示或保存密钥。

更新 `rag_demo/` 下的 Python 模块或接口后，请在启动服务的终端按 `Ctrl+C`，重新执行启动命令，再刷新页面。只刷新浏览器可能使新页面代码调用仍缓存在服务进程中的旧接口。中英文功能更新后曾出现 `output_language` 参数和错误处理函数接口不一致，已通过完整重启解决；已有 SQLite 会话与工单不受重启影响。

## 数据源：本地 JSON / WSL ROS

左侧增加 `数据源 / Data source`：

- `本地 JSON / Local JSON`：沿用三个初始化和三个关节模拟工况，不需要启动 WSL 服务。
- `WSL ROS`：当前只支持关节响应回放。界面不选择本地工况，实际工况由启动的 ROS 桥接器决定，界面显示实际收到的曲线、测试/采集 ID 与指标。

先在项目根目录的另一个 PowerShell 启动并保持运行（不要加 `--verify-only`）：

```powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_load_unknown
```

页面选 `WSL ROS`，确认端口（默认8765），点击“检查并载入 ROS 快照 / Check and load ROS capture”。该按钮只请求/校验证据，不调用模型；只有成功载入才启用开始诊断。看到曲线后再点击开始新诊断。加载后如果桥接服务换成别的 capture，开始时的身份复核会拒绝，不会悄悄绑定新数据。

当前会话顶部标明实际数据源。语言、数据源或本地工况的选择只影响下一次新会话，不能更换已暂停案件的来源。ROS 连接失败、未采集完或快照校验失败会明确提示，绝不切回本地 JSON；且在构造模型客户端之前失败。

新 ROS 会话会保存 `data_source=wsl_ros` 和 capture/hash 等 `source_metadata`，并把完整轨迹与快照缓存到 `data/ros_captures/<capture_id>.json`。后续刷新、澄清、审批从原检查点和本地已校验缓存恢复，不重新连接 ROS。即使桥接服务关闭，也能继续查看原曲线和报告；缓存缺失或被修改时明确提示无法校验，不用其他曲线代替。轨迹不加入模型上下文或 LangGraph 状态，避免每个节点重复携带整个 CSV。

来源同时保留在 Trace metadata 和工单中。来源是“ROS 中传输的离线合成回放”，不是实体传感器新测量，也不是重新运行控制器。ROS 回放细节见 [桥接说明](ros_replay_bridge.md)。更新后台模块后须完整重启 Streamlit。

## 语言与演示顺序

左侧顶部 `语言 / Language` 提供 `中文` 和 `English`。English 模式包含英文工况、指标、按钮、流程状态、澄清问题、事实标签、草稿预览和错误说明。新会话会保存输出语言，模型必须提交对应语言的报告；不符合时进入现有一次纠正/转人工逻辑。新英文工单的默认标题和请求支持文字也为英文，下载 JSON 与原始事实保持对应关系。

建议面试前先选 English，再新建演示会话：

1. 选择超调/振荡，查看曲线和要求，再启动诊断。
2. 在 Diagnosis 中说明事实与推断，在 Evidence & knowledge 中查看对应来源。
3. 使用负载缺失工况展示英文澄清。回复不知道时保留缺口，继续报告及工单。
4. 在 Support ticket 审阅完整草稿，修改后重新确认，或取消。
5. 在 Execution 查看节点历史、用量和已验证的 Trace 入口。

切换语言仅改变展示文字，不自动翻译或覆盖已保存的报告、人工问题/备注、证据和工单。旧中文报告在英文界面保留原文并显示提示；如需完整英文诊断应新开英文会话。已经暂停的会话恢复时沿用其最初输出语言，不借切换界面语言修改已审批内容。切换语言不改变草稿哈希，也不会失效或伪造批准。

原始证据/草稿 JSON 的技术标识、知识来源与双语事实标签保留原始结构；它们不是重新翻译后的数据副本。Matplotlib 曲线原本已使用英文。

## 布局与验证

主内容顶部留白由 2rem 增至 5rem，窄屏为 4.5rem，为 Streamlit 固定工具栏留出空间，修复顶部 `BENCH AI / ENGINEERING SUPPORT DEMO` 被遮挡的问题。

86 项测试通过。界面测试覆盖两种数据源、ROS 载入后才能开始、切换选择不改已有来源、服务离线后的澄清恢复、缓存篡改时不替换曲线、不可用来源不创建模型、载入终端会话、工单修改/审批/去重与中英文切换。工单创建测试使用临时目录，没有批准用户当前工单。

2026-11-08 真实英文验证线程 `ui-english-bf8314a877`：

- 英文负载追问成功，模型调用前暂停；[16 步 Trace 回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/d15827ba-42d0-4857-b1a9-8e4b7f58930b/run/d15827ba-42d0-4857-b1a9-8e4b7f58930b)。
- 使用明确的演示验证回复恢复，报告语言为 `en`、证据评审通过、生成 `BENCH-001 support request`，完整可读草稿无中文；[15 步 Trace 回读](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/3b65259e-9b29-4ab9-a2ce-0ca480ecbd60/run/3b65259e-9b29-4ab9-a2ce-0ca480ecbd60)。该线程停在工单审批，没有自动创建工单。

当前仍有边界：模型节点连接失败后，界面暂不支持从该模型节点重试，需新开会话；已经批准的本地工单创建失败可通过原有幂等路径重试。Trace 上传或回读未验证不会自动重跑模型。已接入 ROS 合成回放，仍无真实设备控制、外部支持系统或公开部署。

2026-11-09 新增真实界面链路验证：WSL 负载缺失回放 → 界面载入601点快照 → 开始英文诊断 → 模型调用前暂停 → 演示回复 → 英文报告及待审批草稿。线程 `38a1c7d28c0644fcbf849b1a9f9cbaf0`，数据源为 `wsl_ros`，草稿保留同一 capture 来源。两个 Trace 均回读通过：[澄清暂停，16步](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e53789ae-6c8b-4424-b770-fec0105fa6da/run/e53789ae-6c8b-4424-b770-fec0105fa6da)、[恢复到工单审批，15步](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/607bb271-ed44-4474-9e38-4fbd88a503f0/run/607bb271-ed44-4474-9e38-4fbd88a503f0)。未自动批准工单。模型评审仍可能漏检重复追问或措辞问题，有限验证不等于语义绝对正确。
