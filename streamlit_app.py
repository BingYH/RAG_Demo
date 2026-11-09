"""Local presentation UI; launch with streamlit run streamlit_app.py."""

import json
import re
from pathlib import Path
from uuid import uuid4

import streamlit as st

from rag_demo.dashboard import DashboardService, failure_message
from rag_demo.tickets import content_hash
from rag_demo.workflow import WORKFLOW_VERSION
from simulator.motion import ROOT as MOTION_ROOT, SCENARIOS, plot_response, verify_fixture
from simulator.http_motion import RosCaptureError
from rag_demo.ui_i18n import translate


def t(text):
    return translate(text, st.session_state.get("ui_language", "zh"))

ROOT = Path(__file__).resolve().parent
SCENARIO_LABELS = {
    "joint_tracking_oscillation": t("关节响应 · 超调与振荡"),
    "joint_tracking_load_unknown": t("关节响应 · 负载信息缺失"),
    "joint_tracking_baseline": t("关节响应 · 基准记录"),
    "connection_timeout": t("初始化 · 连接超时"),
    "version_mismatch": t("初始化 · 协议不匹配"),
    "healthy": t("初始化 · 基准记录"),
}
STATUS = {"awaiting_input": t("等待补充信息"), "awaiting_ticket_approval": t("等待工单审批"),
          "completed": t("诊断完成"), "escalated": t("需要人工核查"), "ticket_created": t("本地工单已创建"),
          "ticket_cancelled": t("工单已取消"), "running": t("执行未结束")}
NODES = {"collect_evidence": t("收集证据"), "retrieve_knowledge": t("检索知识"), "check_evidence": t("检查覆盖"),
         "refine_query": t("补充检索"), "clarify": t("澄清信息"), "generate_report": t("生成报告"),
         "validate_report": t("校验来源"), "review_report": t("评审报告"), "correct_report": t("纠正报告"),
         "finalize": t("发布报告"), "escalate": t("转人工核查"), "prepare_ticket": t("准备工单"),
         "await_ticket_approval": t("等待审批"), "revise_ticket": t("修改草稿"), "create_ticket": t("创建工单"),
         "cancel_ticket": t("取消工单")}


def service():
    return DashboardService()


def run_action(thread_id, **kwargs):
    st.session_state["active_thread"] = thread_id
    try:
        with st.status(t("正在执行工作流…"), expanded=True) as progress:
            def update(node, result):
                st.write("✓ " + NODES.get(node, node))
                if result.get("route"):
                    st.caption(t("下一步：") + NODES.get(result["route"], result["route"]))
            service().execute(thread_id, on_node=update, **kwargs)
            progress.update(label=t("本轮执行完成"), state="complete", expanded=False)
        st.session_state.pop("action_error", None)
    except ValueError as exc:
        if isinstance(exc, RosCaptureError):
            st.session_state["action_error"] = "ROS 快照不可用、未完成或已变化。请检查桥接服务并重新载入；没有回退到本地 JSON。"
            st.session_state["action_error_en"] = "The ROS snapshot is unavailable, incomplete or changed. Check the bridge and reload the capture; no local JSON fallback was used."
        else:
            st.session_state["action_error"] = str(exc)
            st.session_state["action_error_en"] = "The action could not be accepted. Check the thread, current draft revision and required inputs."
    except Exception as exc:
        st.session_state["action_error"] = failure_message(exc)
        st.session_state["action_error_en"] = failure_message(exc, "en")
    st.rerun()


def fact_value(fact):
    value = fact["value"]
    if value is None:
        return t("未知 · ") + fact["unavailable_reason"] if fact.get("unavailable_reason") else t("无")
    if isinstance(value, dict) and "metric_id" in value:
        number = t("未取得") if value["value"] is None else f"{value['value']:.5g} {value['unit']}"
        comparison = t("绝对值 ≤") if value["operator"] == "abs_le" else "≤"
        limit = f"{t('；要求 ')}{comparison} {value['threshold']} {value['unit']}" if value["threshold"] is not None else ""
        return number + limit + ("; " if st.session_state.get("ui_language") == "en" else "；") + {"pass": t("通过"), "fail": t("未通过"), "informational": t("描述性"), "not_evaluable": t("不可评价")}.get(value["result"], value["result"])
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)


@st.cache_data(show_spinner=False)
def preview(scenario, csv_hash):
    state, rows = verify_fixture(MOTION_ROOT / scenario)
    path = ROOT / "data/motion_reports" / (state["test_id"] + "-ui.png")
    plot_response(state, rows, path)
    return state, path.read_bytes()


@st.cache_data(show_spinner=False)
def ros_plot(captured, rows):
    path = ROOT / "data/motion_reports" / (captured["test_id"] + "-ui.png")
    plot_response(captured, rows, path)
    return path.read_bytes()


def show_motion(captured, png):
    data = captured["observations"]["read_motion_test_results"]["data"]
    metrics = {m["metric_id"]: m for m in data["metrics"]}
    a, b, c = st.columns(3)
    a.metric(t("超调"), f"{metrics['overshoot_pct']['value']:.2f}%", t("演示要求 ≤ 5%"), delta_color="off")
    settling = metrics["settling_time_s"]["value"]
    b.metric(t("调节时间"), t("未取得") if settling is None else f"{settling:.2f} s", t("演示要求 ≤ 1.5 s"), delta_color="off")
    c.metric(t("测试条件"), t("完整") if captured["observations"]["read_motion_test_conditions"]["data"]["test_context_status"] == "complete" else t("信息缺失"),
             delta_color="off")
    st.caption(captured["test_id"])
    st.image(png, width="stretch")


def main():
    st.set_page_config(page_title=t("Bench AI · 测试支持工作流"), page_icon="🦾", layout="wide")
    st.markdown("""<style>
        .block-container {max-width:1450px; padding-top:5rem;}
        @media(max-width:800px) {.block-container {padding-top:4.5rem;}}
        h1 {letter-spacing:-.035em;} [data-testid="stMetric"] {background:white;
        border:1px solid #dfe7ef; border-radius:12px; padding:14px;}
        [data-testid="stSidebar"] {border-right:1px solid #dfe7ef;}
        </style>""", unsafe_allow_html=True)
    st.sidebar.selectbox("语言 / Language", ["zh", "en"],
                         format_func=lambda value: "中文" if value == "zh" else "English", key="ui_language")
    st.caption("BENCH AI  /  ENGINEERING SUPPORT DEMO")
    st.title(t("从测试异常，到有依据的下一步"))
    st.write(t("查看响应、收集证据、澄清缺口，并由工程师确认支持工单。"))
    st.caption(t("BENCH-001 · 离线合成数据 · 本地演示工单"))
    active = st.session_state.get("active_thread")
    view = {"state": {}, "interrupts": [], "runs": []}
    if active:
        try:
            view = service().read(active)
        except Exception:
            st.error(t("无法读取会话，请检查本地状态文件。"))
    state = view["state"]
    compatible = not state or state.get("workflow_version") == WORKFLOW_VERSION

    with st.sidebar:
        st.subheader(t("演示台架"))
        source_labels = {"local_json": t("本地 JSON"), "wsl_ros": "WSL ROS"}
        data_source = st.selectbox(t("数据源"), list(source_labels), format_func=source_labels.get, key="data_source")
        ros_port, ros_preview = None, None
        if data_source == "local_json":
            scenario = st.selectbox(t("选择工况"), list(SCENARIO_LABELS), format_func=SCENARIO_LABELS.get, key="scenario")
            motion = scenario in SCENARIOS
        else:
            scenario, motion = None, True
            st.caption(t("WSL ROS 当前仅支持关节响应回放。"))
            ros_port = int(st.number_input(t("ROS 桥接端口"), min_value=1024, max_value=65535, value=8765, step=1, key="ros_port"))
            st.caption(t("先在终端启动回放桥接器，保持运行；不要使用 --verify-only。"))
            with st.expander(t("启动命令")):
                st.code(f".\\.venv\\Scripts\\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation --port {ros_port}", language="powershell")
            if st.button(t("检查并载入 ROS 快照"), key="load_ros", use_container_width=True):
                st.session_state.pop("ros_preview", None)
                try:
                    with st.spinner(t("正在读取并校验 ROS 快照…")):
                        payload = service().fetch_ros(ros_port)
                    st.session_state["ros_preview"] = {"port": ros_port, "payload": payload}
                    st.session_state.pop("ros_preview_error", None)
                except Exception:
                    st.session_state["ros_preview_error"] = True
            cached = st.session_state.get("ros_preview")
            if cached and cached["port"] == ros_port:
                ros_preview = cached["payload"]
                st.success(t("采集与校验成功；响应是否合格请看指标。"))
                st.caption("Capture: " + ros_preview["capture_id"])
            if st.session_state.get("ros_preview_error"):
                st.error(t("ROS 快照不可用或尚未采集完成。请检查桥接服务；不会回退到 JSON。"))
        default_question = (t("请分析这次单关节响应测试，说明超限指标、可能原因和下一步。") if motion else
                            t("更新后台架初始化失败，请根据证据帮助排查。"))
        with st.form("new_diagnosis"):
            question = st.text_area(t("测试问题"), value=default_question, max_chars=4000, key=f"question-{scenario}-{st.session_state['ui_language']}")
            ticket = st.checkbox(t("诊断后准备支持工单"), value=True, key="request_ticket")
            start = st.form_submit_button(t("开始新诊断"), type="primary", use_container_width=True,
                                          disabled=data_source == "wsl_ros" and ros_preview is None)
        st.caption(t("开始新诊断会创建独立会话并调用模型 API。切换工况不会改变已有会话。"))
        if start:
            source_args = ({"ros_port": ros_port, "expected_capture_id": ros_preview["capture_id"]}
                           if data_source == "wsl_ros" else {})
            run_action(uuid4().hex, task_type="joint_response" if motion else "initialization", data_source=data_source,
                       scenario=scenario, question=question, ticket=ticket,
                       output_language=st.session_state["ui_language"], **source_args)
        st.caption(t("数据源选项仅影响新会话；当前会话的证据来源不会切换。"))
        st.divider()
        with st.form("load_thread"):
            requested = st.text_input(t("载入已有会话"), placeholder=t("粘贴终端中的 Thread ID"), key="load_id")
            load = st.form_submit_button(t("载入会话"), use_container_width=True)
        if load:
            try:
                loaded = service().read(requested.strip())
                if not loaded["state"]:
                    st.error(t("没有找到该会话。"))
                else:
                    st.session_state["active_thread"] = requested.strip()
                    st.session_state.pop("action_error", None)
                    st.rerun()
            except ValueError as exc:
                st.error("Unable to open that thread. Check its ID and saved checkpoint." if st.session_state["ui_language"] == "en" else str(exc))
        if active:
            st.caption(t("当前会话"))
            st.code(active, language=None)
            if st.button(t("刷新会话"), use_container_width=True):
                st.rerun()
            if st.button(t("返回工况预览"), use_container_width=True):
                st.session_state.pop("active_thread", None)
                st.session_state.pop("action_error", None)
                st.rerun()

    if st.session_state.get("action_error"):
        st.error(st.session_state.get("action_error_en", "The previous action did not finish. Check the saved thread.") if st.session_state["ui_language"] == "en" else st.session_state["action_error"])
    if not compatible:
        st.warning(t("该会话属于旧工作流，可查看记录；继续操作请开始新会话。"))
    if state:
        st.info(t("当前案件：") + (t("关节响应诊断") if state["task_type"] == "joint_response" else t("初始化诊断")) +
                "  ·  " + STATUS.get(state["status"], state["status"]))
        st.caption(t("问题：") + state["question"])
        st.caption(t("当前会话数据源：") + ("WSL ROS" if state.get("data_source") == "wsl_ros" else t("本地 JSON")))
        if state.get("source_metadata", {}).get("capture_id"):
            st.caption("Capture: " + state["source_metadata"]["capture_id"] + " · " + t("离线合成回放；固定采集快照"))
    else:
        st.info(t("工况预览 · 尚未开始 AI 诊断。选择工况后可先查看曲线与已记录指标。"))

    shown_scenario = scenario
    ros_motion = None
    if state.get("data_source") == "wsl_ros":
        ros_motion = view.get("motion")
        if view.get("motion_error"):
            st.warning(t("本会话的已保存 ROS 曲线无法校验；未显示替代的 JSON 曲线。报告与证据仍可查看。"))
    elif not state and data_source == "wsl_ros" and ros_preview:
        ros_motion = {"state": ros_preview["snapshot"], "rows": ros_preview["trajectory"]}
    if ros_motion:
        show_motion(ros_motion["state"], ros_plot(ros_motion["state"], ros_motion["rows"]))
    if state:
        test = (state.get("evidence", {}).get("read_motion_test_conditions", {}).get("data") or {}).get("test_id")
        shown_scenario = {"TEST-104": SCENARIOS[0], "TEST-218": SCENARIOS[1], "TEST-307": SCENARIOS[2]}.get(test)
    if shown_scenario in SCENARIOS:
        try:
            fixture, _ = verify_fixture(MOTION_ROOT / shown_scenario)
            data = fixture["observations"]["read_motion_test_results"]["data"]
            saved = (state.get("evidence", {}).get("read_motion_test_results", {}).get("data") or {})
            if saved and saved.get("trajectory_sha256") != data["trajectory_sha256"]:
                st.warning(t("当前文件与已保存证据的轨迹版本不同，未显示替代曲线。请查看原会话证据。"))
            else:
                _, png = preview(shown_scenario, data["trajectory_sha256"])
                show_motion(fixture, png)
        except (OSError, ValueError, KeyError):
            st.warning(t("曲线素材无法通过校验，请先运行 scripts/generate_motion_fixtures.py。"))

    if not state:
        if not motion:
            st.write(t("该工况将读取登记信息、运行配置、连接观察、初始化状态和诊断日志。"))
        st.caption(t("工作流：收集证据 → 检索 → 检查缺口 → 澄清或生成 → 校验与评审 → 人工确认工单"))
        return

    report_tab, evidence_tab, ticket_tab, trace_tab = st.tabs([t("诊断报告"), t("证据与知识"), t("支持工单"), t("执行过程")])
    with report_tab:
        if state["status"] == "awaiting_input" and compatible:
            payload = next((p for p in view["interrupts"] if p.get("kind") == "clarification"), None)
            if state.get("task_type") == "joint_response":
                st.warning(t("本次关节测试的负载条件记录不完整。请说明使用的工具/夹具与负载、是否发生更换，以及是否有对应记录；如果暂不清楚，请直接说明。"))
            else:
                target = (state.get("evidence", {}).get("read_runtime_config", {}).get("data") or {}).get("target_ip")
                registered = (state.get("evidence", {}).get("read_bench_inventory", {}).get("data") or {}).get("registered_controller_address")
                st.warning((f"Configured endpoint: {target}; registered endpoint: {registered}. Was this change intentional? Share the intended target, or say you do not know."
                            if st.session_state["ui_language"] == "en" else payload["question"] if payload else t("需要补充现场背景，请说明已知信息；不清楚也可如实回答。")))
            with st.form("clarification-" + active):
                reply = st.text_area(t("补充说明"), max_chars=2000, key="reply-" + active)
                submit = st.form_submit_button(t("提交说明并继续"), type="primary")
            st.caption(t("说明作为未验证背景保存，不会覆盖原始证据。"))
            if submit:
                run_action(active, decision=reply)
        if state.get("answer"):
            if state.get("report", {}).get("language", "zh") != st.session_state["ui_language"]:
                st.info(t("原报告语言与当前界面不同。已保存的报告和人工输入保留原文；如需英文诊断，请以 English 新建会话。"))
            rendered = state.get("report", {}).get("rendered_fact_ids", []) if state.get("diagnosis_status") == "completed" else []
            if rendered:
                st.subheader(t("事实与来源"))
                st.dataframe([{t("事实"): state["facts"][fid]["labels"][1 if st.session_state["ui_language"] == "en" else 0], t("记录值"): fact_value(state["facts"][fid]),
                               t("证据"): state["facts"][fid]["evidence_id"]} for fid in rendered], hide_index=True, width="stretch")
                parts = re.split(r"(?m)^## (?:解读|Interpretation)", state["answer"], maxsplit=1)
                st.markdown(t("## 解读") + parts[1] if len(parts) == 2 else state["answer"])
            else:
                st.markdown(state["answer"])
        elif state["status"] != "awaiting_input":
            st.write(t("尚无通过校验与评审的报告。"))

    with evidence_tab:
        st.subheader(t("已收集证据"))
        for name, envelope in state.get("evidence", {}).items():
            with st.expander(f"{name} · {envelope.get('status')} · {envelope.get('evidence_id', '')}"):
                st.json(envelope)
        st.subheader(t("检索依据"))
        chunks = state.get("chunks", {})
        if chunks:
            selected = st.selectbox(t("查看知识片段"), list(chunks), format_func=lambda k: k + " · " + chunks[k].get("section", ""))
            chunk = chunks[selected]
            st.caption(t("文档版本 {version} · 适用范围 {scope}").format(version=chunk.get('version', ''), scope=chunk.get('applies_to', '')))
            st.write(chunk["text"])
        else:
            st.write(t("尚未检索到可引用的知识片段。"))

    with ticket_tab:
        draft = state.get("ticket_draft")
        if draft:
            st.subheader(t("工单草稿") + f" · r{draft['revision']}")
            st.write(draft["title"])
            st.caption(t("快照") + f" {draft['snapshot_id']} · " + t("测试") + f" {draft.get('test_id') or draft.get('startup_attempt_id')}")
            st.write(draft["description"])
            st.write(t("请求支持：") + draft["requested_support"])
            st.write(t("工程师备注：") + (draft["engineer_notes"] or t("无")))
            if draft["evidence_gaps"]:
                st.warning(t("保留的证据缺口：") + "；".join(draft["evidence_gaps"]))
            with st.expander(t("完整草稿与引用"), expanded=False):
                from rag_demo.tickets import render_draft
                st.markdown(render_draft(draft, language=st.session_state["ui_language"]))
                st.json(draft)
            st.download_button(t("下载完整草稿 JSON"), json.dumps(draft, ensure_ascii=False, indent=2),
                               file_name=f"ticket-draft-r{draft['revision']}.json", mime="application/json")
            if state["status"] == "awaiting_ticket_approval" and compatible:
                digest = content_hash(draft)
                with st.expander(t("修改草稿文字")):
                    with st.form("edit-" + digest):
                        edits = {key: st.text_area(label, value=draft[key], max_chars=limit, key=digest + key)
                                 for key, label, limit in (("title", t("标题"), 160), ("description", t("问题描述"), 4000),
                                     ("requested_support", t("请求支持"), 2000), ("engineer_notes", t("工程师备注"), 2000))}
                        edit = st.form_submit_button(t("保存修改并重新审批"))
                    if edit:
                        run_action(active, decision={"action": "edit", "draft_hash": digest, "edits": edits})
                with st.form("approve-" + digest):
                    confirmed = st.checkbox(t("我已审阅完整草稿，确认创建这份本地演示工单"), key="reviewed-" + digest)
                    approve = st.form_submit_button(t("确认创建本地工单"), type="primary")
                if approve:
                    if confirmed:
                        run_action(active, decision={"action": "approve", "draft_hash": digest})
                    else:
                        st.warning(t("请先审阅完整草稿并勾选确认。"))
                if st.button(t("取消这份工单"), key="cancel-" + digest):
                    run_action(active, decision={"action": "cancel"})
        elif not state.get("ticket_requested"):
            st.info(t("本会话仅请求诊断。若需演示工单，请新建会话并勾选准备支持工单。"))
        else:
            st.info(t("诊断完成后将准备草稿；目前尚未创建工单。"))
        if state.get("ticket"):
            st.success(t("本地工单：") + state["ticket"]["ticket_id"])
        if state["status"] == "ticket_cancelled":
            st.info(t("工单已取消，未创建本地记录。"))
        st.caption(t("工单只保存在本地。确认不授权设备运动或控制参数变更。"))

    with trace_tab:
        st.subheader(t("节点执行记录"))
        st.write(" → ".join(NODES.get(n, n) for n in state.get("node_history", [])))
        usage = state.get("usage", {})
        st.caption(t("整个会话用量：输入 {input:,} / 输出 {output:,} tokens").format(input=usage.get('input_tokens', 0), output=usage.get('output_tokens', 0)))
        for run in view["runs"]:
            if run["trace_url"]:
                st.link_button((t("已验证 Trace · ") if run["trace_verified"] else "Trace · ") + run["run_id"][:8], run["trace_url"])
            else:
                st.caption(t("运行 ") + run["run_id"] + t(" · Trace 链接未记录，可在 LangSmith 按会话编号查看。"))
        if state.get("evidence_reviews"):
            with st.expander(t("报告评审结果")):
                st.json(state["evidence_reviews"])
        st.caption(t("会话编号：") + active)
        if state["status"] == "running" and compatible:
            st.warning(t("本轮执行未结束。可刷新检查；模型节点异常目前需要新开会话。本地工单创建失败可安全重试。"))
            if st.button(t("重试已批准的工单创建")):
                run_action(active, retry=True)


if __name__ == "__main__":
    main()
