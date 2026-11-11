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
    return translate(text, st.session_state.get("ui_language", "en"))

ROOT = Path(__file__).resolve().parent
SCENARIO_LABELS = {
    "joint_tracking_oscillation": t('Joint response · Overshoot and oscillation'),
    "joint_tracking_load_unknown": t('Joint response · Missing load context'),
    "joint_tracking_baseline": t('Joint response · Baseline'),
    "connection_timeout": t('Initialization · Connection timeout'),
    "version_mismatch": t('Initialization · Protocol mismatch'),
    "healthy": t('Initialization · Baseline'),
}
STATUS = {"awaiting_input": t('Awaiting clarification'), "awaiting_ticket_approval": t('Awaiting ticket approval'),
          "completed": t('Diagnosis complete'), "escalated": t('Engineering review needed'), "ticket_created": t('Local ticket created'),
          "ticket_cancelled": t('Ticket cancelled'), "running": t('Run not finished')}
NODES = {"collect_evidence": t('Collect evidence'), "retrieve_knowledge": t('Retrieve knowledge'), "check_evidence": t('Check coverage'),
         "refine_query": t('Refine retrieval'), "clarify": t('Clarify context'), "generate_report": t('Generate report'),
         "validate_report": t('Validate sources'), "review_report": t('Review report'), "correct_report": t('Correct report'),
         "finalize": t('Publish report'), "escalate": t('Escalate for review'), "prepare_ticket": t('Prepare ticket'),
         "await_ticket_approval": t('Await approval'), "revise_ticket": t('Revise draft'), "create_ticket": t('Create ticket'),
         "cancel_ticket": t('Cancel ticket')}


def service():
    return DashboardService()


def run_action(thread_id, **kwargs):
    st.session_state["active_thread"] = thread_id
    try:
        with st.status(t('Running workflow…'), expanded=True) as progress:
            def update(node, result):
                st.write("✓ " + NODES.get(node, node))
                if result.get("route"):
                    st.caption(t('Next: ') + NODES.get(result["route"], result["route"]))
            service().execute(thread_id, on_node=update, **kwargs)
            progress.update(label=t('This run is complete'), state="complete", expanded=False)
        st.session_state.pop("action_error", None)
    except ValueError as exc:
        if isinstance(exc, RosCaptureError):
            st.session_state["action_error"] = 'The ROS capture is unavailable, incomplete or changed. Check the bridge and reload; no local JSON fallback was used.'
            st.session_state["action_error_en"] = "The ROS snapshot is unavailable, incomplete or changed. Check the bridge and reload the capture; no local JSON fallback was used."
        else:
            st.session_state["action_error"] = translate(str(exc), "zh")
            st.session_state["action_error_en"] = "The action could not be accepted. Check the thread, current draft revision and required inputs."
    except Exception as exc:
        st.session_state["action_error"] = failure_message(exc, "zh")
        st.session_state["action_error_en"] = failure_message(exc, "en")
    st.rerun()


def fact_value(fact):
    value = fact["value"]
    if value is None:
        return t('Unknown · ') + fact["unavailable_reason"] if fact.get("unavailable_reason") else t('None')
    if isinstance(value, dict) and "metric_id" in value:
        number = t('Unavailable') if value["value"] is None else f"{value['value']:.5g} {value['unit']}"
        comparison = t('absolute value ≤') if value["operator"] == "abs_le" else "≤"
        limit = f"{t('; limit ')}{comparison} {value['threshold']} {value['unit']}" if value["threshold"] is not None else ""
        return number + limit + ("; " if st.session_state.get("ui_language") == "en" else "；") + {"pass": t('Pass'), "fail": t('Fail'), "informational": t('Informational'), "not_evaluable": t('Not evaluable')}.get(value["result"], value["result"])
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
    a.metric(t('Overshoot'), f"{metrics['overshoot_pct']['value']:.2f}%", t('Demo limit ≤ 5%'), delta_color="off")
    settling = metrics["settling_time_s"]["value"]
    b.metric(t('Settling time'), t('Unavailable') if settling is None else f"{settling:.2f} s", t('Demo limit ≤ 1.5 s'), delta_color="off")
    c.metric(t('Test context'), t('Complete') if captured["observations"]["read_motion_test_conditions"]["data"]["test_context_status"] == "complete" else t('Incomplete'),
             delta_color="off")
    st.caption(captured["test_id"])
    st.image(png, width="stretch")


def main():
    st.set_page_config(page_title=t('Bench AI · Engineering support workflow'), page_icon="🦾", layout="wide")
    st.markdown("""<style>
        .block-container {max-width:1450px; padding-top:5rem;}
        @media(max-width:800px) {.block-container {padding-top:4.5rem;}}
        h1 {letter-spacing:-.035em;} [data-testid="stMetric"] {background:white;
        border:1px solid #dfe7ef; border-radius:12px; padding:14px;}
        [data-testid="stSidebar"] {border-right:1px solid #dfe7ef;}
        </style>""", unsafe_allow_html=True)
    st.sidebar.selectbox('Language', ["en", "zh"],
                         format_func=lambda value: 'Chinese' if value == "zh" else "English", key="ui_language")
    st.caption("BENCH AI  /  ENGINEERING SUPPORT DEMO")
    st.title(t('From test anomalies to evidence-based action'))
    st.write(t('Inspect responses, gather evidence, clarify gaps and review support tickets with an engineer.'))
    st.caption(t('BENCH-001 · Offline synthetic data · Local demo tickets'))
    active = st.session_state.get("active_thread")
    view = {"state": {}, "interrupts": [], "runs": []}
    if active:
        try:
            view = service().read(active)
        except Exception:
            st.error(t('Unable to read the thread. Check the local checkpoint.'))
    state = view["state"]
    compatible = not state or state.get("workflow_version") == WORKFLOW_VERSION

    with st.sidebar:
        st.subheader(t('Demo bench'))
        source_labels = {"local_json": t('Local JSON'), "wsl_ros": "WSL ROS"}
        data_source = st.selectbox(t('Data source'), list(source_labels), format_func=source_labels.get, key="data_source")
        ros_port, ros_preview = None, None
        if data_source == "local_json":
            scenario = st.selectbox(t('Scenario'), list(SCENARIO_LABELS), format_func=SCENARIO_LABELS.get, key="scenario")
            motion = scenario in SCENARIOS
        else:
            scenario, motion = None, True
            st.caption(t('WSL ROS currently supports joint response replay only.'))
            ros_port = int(st.number_input(t('ROS bridge port'), min_value=1024, max_value=65535, value=8765, step=1, key="ros_port"))
            st.caption(t('Start the replay bridge in a terminal and keep it running; do not use --verify-only.'))
            with st.expander(t('Start command')):
                st.code(f".\\.venv\\Scripts\\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation --port {ros_port}", language="powershell")
            if st.button(t('Check and load ROS capture'), key="load_ros", use_container_width=True):
                st.session_state.pop("ros_preview", None)
                try:
                    with st.spinner(t('Reading and validating ROS capture…')):
                        payload = service().fetch_ros(ros_port)
                    st.session_state["ros_preview"] = {"port": ros_port, "payload": payload}
                    st.session_state.pop("ros_preview_error", None)
                except Exception:
                    st.session_state["ros_preview_error"] = True
            cached = st.session_state.get("ros_preview")
            if cached and cached["port"] == ros_port:
                ros_preview = cached["payload"]
                st.success(t('Capture and validation succeeded. Check the metrics for response pass/fail.'))
                st.caption("Capture: " + ros_preview["capture_id"])
            if st.session_state.get("ros_preview_error"):
                st.error(t('ROS capture is unavailable or incomplete. Check the bridge; no JSON fallback will be used.'))
        default_question = (t('Analyze this single-joint response test. Explain failed requirements, possible causes and next steps. Reply in English.') if motion else
                            t('Bench initialization failed after an update. Investigate using the available evidence. Reply in English.'))
        with st.form("new_diagnosis"):
            question = st.text_area(t('Test question'), value=default_question, max_chars=4000, key=f"question-{scenario}-{st.session_state['ui_language']}")
            ticket = st.checkbox(t('Prepare a support ticket after diagnosis'), value=True, key="request_ticket")
            start = st.form_submit_button(t('Start new diagnosis'), type="primary", use_container_width=True,
                                          disabled=data_source == "wsl_ros" and ros_preview is None)
        st.caption(t('A new diagnosis creates a separate thread and calls the model API. Scenario selection does not change an existing case.'))
        if start:
            source_args = ({"ros_port": ros_port, "expected_capture_id": ros_preview["capture_id"]}
                           if data_source == "wsl_ros" else {})
            run_action(uuid4().hex, task_type="joint_response" if motion else "initialization", data_source=data_source,
                       scenario=scenario, question=question, ticket=ticket,
                       output_language=st.session_state["ui_language"], **source_args)
        st.caption(t("Source selection affects new threads only. The current thread's evidence source stays fixed."))
        st.divider()
        with st.form("load_thread"):
            requested = st.text_input(t('Open an existing thread'), placeholder=t('Paste the Thread ID from the terminal'), key="load_id")
            load = st.form_submit_button(t('Open thread'), use_container_width=True)
        if load:
            try:
                loaded = service().read(requested.strip())
                if not loaded["state"]:
                    st.error(t('Thread not found.'))
                else:
                    st.session_state["active_thread"] = requested.strip()
                    st.session_state.pop("action_error", None)
                    st.rerun()
            except ValueError as exc:
                st.error("Unable to open that thread. Check its ID and saved checkpoint." if st.session_state["ui_language"] == "en" else str(exc))
        if active:
            st.caption(t('Current thread'))
            st.code(active, language=None)
            if st.button(t('Refresh thread'), use_container_width=True):
                st.rerun()
            if st.button(t('Back to scenario preview'), use_container_width=True):
                st.session_state.pop("active_thread", None)
                st.session_state.pop("action_error", None)
                st.rerun()

    if st.session_state.get("action_error"):
        st.error(st.session_state.get("action_error_en", "The previous action did not finish. Check the saved thread.") if st.session_state["ui_language"] == "en" else st.session_state["action_error"])
    if not compatible:
        st.warning(t('This thread uses an older workflow. You can view it; start a new thread to continue.'))
    if state:
        st.info(t('Current case: ') + (t('Joint response diagnosis') if state["task_type"] == "joint_response" else t('Initialization diagnosis')) +
                "  ·  " + STATUS.get(state["status"], state["status"]))
        st.caption(t('Question: ') + state["question"])
        st.caption(t('Current thread source: ') + ("WSL ROS" if state.get("data_source") == "wsl_ros" else t('Local JSON')))
        if state.get("source_metadata", {}).get("capture_id"):
            st.caption("Capture: " + state["source_metadata"]["capture_id"] + " · " + t('Offline synthetic replay; frozen capture'))
    else:
        st.info(t('Scenario preview · No AI diagnosis has started. Inspect the curve and recorded metrics first.'))

    shown_scenario = scenario
    ros_motion = None
    if state.get("data_source") == "wsl_ros":
        ros_motion = view.get("motion")
        if view.get("motion_error"):
            st.warning(t('The saved ROS curve could not be validated. No replacement JSON curve is shown; the report and evidence remain available.'))
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
                st.warning(t('The current trajectory differs from the saved evidence. No replacement curve is shown; inspect the original case evidence.'))
            else:
                _, png = preview(shown_scenario, data["trajectory_sha256"])
                show_motion(fixture, png)
        except (OSError, ValueError, KeyError):
            st.warning(t('Curve validation failed. Run scripts/generate_motion_fixtures.py first.'))

    if not state:
        if not motion:
            st.write(t('This scenario reads registry data, runtime configuration, connection observations, initialization status and diagnostic logs.'))
        st.caption(t('Workflow: collect → retrieve → check gaps → clarify or generate → validate and review → approve ticket'))
        return

    report_tab, evidence_tab, ticket_tab, trace_tab = st.tabs([t('Diagnosis'), t('Evidence & knowledge'), t('Support ticket'), t('Execution')])
    with report_tab:
        if state["status"] == "awaiting_input" and compatible:
            payload = next((p for p in view["interrupts"] if p.get("kind") == "clarification"), None)
            if state.get("task_type") == "joint_response":
                st.warning(t('The load context for this joint test is incomplete. Which tool/fixture and payload were used, did they change, and is a corresponding record available? If you do not know, please say so.'))
            else:
                target = (state.get("evidence", {}).get("read_runtime_config", {}).get("data") or {}).get("target_ip")
                registered = (state.get("evidence", {}).get("read_bench_inventory", {}).get("data") or {}).get("registered_controller_address")
                st.warning((f"Configured endpoint: {target}; registered endpoint: {registered}. Was this change intentional? Share the intended target, or say you do not know."
                            if st.session_state["ui_language"] == "en" else payload["question"] if payload else t('Additional context is needed. Share what you know; it is fine to say you do not know.')))
            with st.form("clarification-" + active):
                reply = st.text_area(t('Additional context'), max_chars=2000, key="reply-" + active)
                submit = st.form_submit_button(t('Submit context and continue'), type="primary")
            st.caption(t('Your statement is stored as unverified context and does not overwrite recorded evidence.'))
            if submit:
                run_action(active, decision=reply)
        if state.get("answer"):
            if state.get("report", {}).get("language", "en") != st.session_state["ui_language"]:
                st.info(t('The saved report uses a different language. Existing text and human input remain unchanged. Start a new English thread for an English diagnosis.'))
            rendered = state.get("report", {}).get("rendered_fact_ids", []) if state.get("diagnosis_status") == "completed" else []
            if rendered:
                st.subheader(t('Facts and sources'))
                st.dataframe([{t('Fact'): state["facts"][fid]["labels"][1 if st.session_state["ui_language"] == "en" else 0], t('Recorded value'): fact_value(state["facts"][fid]),
                               t('Evidence'): state["facts"][fid]["evidence_id"]} for fid in rendered], hide_index=True, width="stretch")
                parts = re.split(r"(?m)^## (?:" + re.escape(translate("Interpretation", "zh")) + r"|Interpretation)", state["answer"], maxsplit=1)
                st.markdown(t('## Interpretation') + parts[1] if len(parts) == 2 else state["answer"])
            else:
                st.markdown(state["answer"])
        elif state["status"] != "awaiting_input":
            st.write(t('No validated and reviewed report is available yet.'))

    with evidence_tab:
        st.subheader(t('Collected evidence'))
        for name, envelope in state.get("evidence", {}).items():
            with st.expander(f"{name} · {envelope.get('status')} · {envelope.get('evidence_id', '')}"):
                st.json(envelope)
        st.subheader(t('Retrieved knowledge'))
        chunks = state.get("chunks", {})
        if chunks:
            selected = st.selectbox(t('Knowledge passage'), list(chunks), format_func=lambda k: k + " · " + chunks[k].get("section", ""))
            chunk = chunks[selected]
            st.caption(t('Document version {version} · Scope {scope}').format(version=chunk.get('version', ''), scope=chunk.get('applies_to', '')))
            st.write(chunk["text"])
        else:
            st.write(t('No citable knowledge passages have been retrieved yet.'))

    with ticket_tab:
        draft = state.get("ticket_draft")
        if draft:
            from rag_demo.tickets import render_draft

            st.caption(t('Demo support ticket') + "  /  " + t('Ticket draft') + f" r{draft['revision']}")
            st.header(draft["title"])
            st.caption(t('This local demonstration is not connected to Jira.'))
            issue, details = st.columns([2.3, 1], gap="large")
            with issue:
                st.subheader(t('Issue description'))
                st.write(draft["description"])
                st.subheader(t('Observed facts'))
                facts = draft.get("facts", [])
                if facts:
                    st.dataframe([{t('Fact'): fact.get('labels', ['', ''])[1 if st.session_state["ui_language"] == "en" else 0],
                                   t('Recorded value'): fact_value(fact), t('Evidence'): fact.get('evidence_id', '')}
                                  for fact in facts], hide_index=True, width="stretch")
                else:
                    st.caption(t('No facts were recorded.'))
                st.subheader(t('Analysis and hypotheses'))
                by_id = {fact['fact_id']: fact for fact in facts}
                for claim in draft.get('interpretations', []):
                    refs = list(dict.fromkeys([by_id[f]['evidence_id'] for f in claim.get('fact_ids', []) if f in by_id] + claim.get('chunk_ids', [])))
                    st.write(claim['text'])
                    if refs:
                        st.caption(' · '.join(refs))
                if not draft.get('interpretations'):
                    st.caption(t('No reviewed interpretation is available.'))
                st.subheader(t('Open questions and evidence gaps'))
                gaps = draft.get('unresolved_questions', []) + draft.get('evidence_gaps', [])
                if gaps:
                    for gap in gaps:
                        st.warning(gap, icon="⚠️")
                else:
                    st.caption(t('No open questions or evidence gaps recorded.'))
                st.subheader(t('Recommended next steps'))
                for number, step in enumerate(draft.get('proposed_next_steps', []), 1):
                    st.write(f"{number}. {step}")
                if not draft.get('proposed_next_steps'):
                    st.caption(t('No next steps recorded.'))
                st.subheader(t('Requested support'))
                st.write(draft['requested_support'])
                st.subheader(t('User context (unverified)'))
                st.write(draft.get('user_context_unverified') or t('None'))
                st.subheader(t('Engineer notes'))
                st.write(draft.get('engineer_notes') or t('None'))
            with details:
                st.subheader(t('Issue details'))
                st.caption(t('Ticket status'))
                st.write(STATUS.get(state['status'], state['status']))
                for label, value in ((t('Draft revision'), f"r{draft['revision']}"),
                                     (t('Bench'), draft.get('bench_id')),
                                     (t('Data source'), draft.get('data_source', 'local_json')),
                                     (t('Snapshot'), draft.get('snapshot_id')),
                                     (t('Test or startup attempt'), draft.get('test_id') or draft.get('startup_attempt_id'))):
                    st.caption(label)
                    st.write(value or t('None'))
                if state.get('ticket'):
                    st.caption(t('Local ticket: '))
                    st.code(state['ticket']['ticket_id'])
                st.divider()
                readable = render_draft(draft, language=st.session_state["ui_language"])
                st.download_button(t('Download readable draft'), readable,
                                   file_name=f"ticket-draft-r{draft['revision']}.md", mime="text/markdown")
                st.download_button(t('Download full draft JSON'), json.dumps(draft, ensure_ascii=False, indent=2),
                                   file_name=f"ticket-draft-r{draft['revision']}.json", mime="application/json")
            with st.expander(t('References and raw data'), expanded=False):
                st.markdown(readable)
                st.json(draft)
            if state["status"] == "awaiting_ticket_approval" and compatible:
                st.divider()
                st.subheader(t('Approval and actions'))
                digest = content_hash(draft)
                with st.expander(t('Edit draft text')):
                    with st.form("edit-" + digest):
                        edits = {key: st.text_area(label, value=draft[key], max_chars=limit, key=digest + key)
                                 for key, label, limit in (("title", t('Title'), 160), ("description", t('Description'), 4000),
                                     ("requested_support", t('Requested support'), 2000), ("engineer_notes", t('Engineer notes'), 2000))}
                        edit = st.form_submit_button(t('Save changes for re-approval'))
                    if edit:
                        run_action(active, decision={"action": "edit", "draft_hash": digest, "edits": edits})
                with st.form("approve-" + digest):
                    confirmed = st.checkbox(t('I have reviewed the full draft and approve creating this local demo ticket'), key="reviewed-" + digest)
                    approve = st.form_submit_button(t('Approve and create local ticket'), type="primary")
                if approve:
                    if confirmed:
                        run_action(active, decision={"action": "approve", "draft_hash": digest})
                    else:
                        st.warning(t('Review the full draft and check the approval box first.'))
                if st.button(t('Cancel this ticket'), key="cancel-" + digest):
                    run_action(active, decision={"action": "cancel"})
        elif not state.get("ticket_requested"):
            st.info(t('This thread requests diagnosis only. For a ticket, start a new thread with the ticket option enabled.'))
        else:
            st.info(t('A draft will be prepared after diagnosis. No ticket has been created yet.'))
        if state.get("ticket"):
            st.success(t('Local ticket: ') + state["ticket"]["ticket_id"])
        if state["status"] == "ticket_cancelled":
            st.info(t('The draft was cancelled; no local ticket was created.'))
        st.caption(t('Tickets stay local. Approval does not authorize motion or controller changes.'))

    with trace_tab:
        st.subheader(t('Node execution history'))
        st.write(" → ".join(NODES.get(n, n) for n in state.get("node_history", [])))
        usage = state.get("usage", {})
        st.caption(t('Thread usage: {input:,} input / {output:,} output tokens').format(input=usage.get('input_tokens', 0), output=usage.get('output_tokens', 0)))
        for run in view["runs"]:
            if run["trace_url"]:
                st.link_button((t('Verified trace · ') if run["trace_verified"] else "Trace · ") + run["run_id"][:8], run["trace_url"])
            else:
                st.caption(t('Run ') + run["run_id"] + t(' · Trace URL not recorded. Search LangSmith using the Thread ID.'))
        if state.get("evidence_reviews"):
            with st.expander(t('Evidence review results')):
                st.json(state["evidence_reviews"])
        st.caption(t('Thread ID: ') + active)
        if state["status"] == "running" and compatible:
            st.warning(t('This run has not finished. Refresh to check. Model failures currently require a new thread; approved local ticket creation can be retried safely.'))
            if st.button(t('Retry approved ticket creation')):
                run_action(active, retry=True)


if __name__ == "__main__":
    main()
