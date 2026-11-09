"""UI adapter over the existing graph/checkpoints. Rendering never calls a model."""

import json
import hashlib
import os
import re
import threading
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import trace, tracing_context

from rag_demo.workflow import TASK_SCOPES, WORKFLOW_VERSION, build_workflow, initial_state
from rag_demo.tickets import TicketStore
from scripts.graph_bench import check_resume, check_retry
from simulator.motion import SCENARIOS as MOTION_SCENARIOS
from simulator.motion_tools import MotionSession
from simulator.tools import DiagnosticSession, SCENARIOS as INIT_SCENARIOS
from simulator.http_motion import HttpMotionSession, RosCaptureError
from simulator.ros_capture import validate_capture

ROOT = Path(__file__).resolve().parents[1]
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def failure_message(exc, language="zh"):
    """Explain SDK failures without exposing response bodies or credentials."""
    from anthropic import APIConnectionError, APITimeoutError, APIStatusError
    if language == "en":
        if isinstance(exc, APITimeoutError):
            return "The model request timed out. Check the server connection; this does not establish a credit issue. Recorded evidence is preserved."
        if isinstance(exc, APIConnectionError):
            return "Cannot connect to the model API; no server response was received. This is not a credit-balance error. Check network permissions and proxy settings. Recorded evidence is preserved."
        if isinstance(exc, APIStatusError):
            body = getattr(exc, "body", None)
            error = body.get("error", body) if isinstance(body, dict) else {}
            message = str(error.get("message", "")).lower() if isinstance(error, dict) else ""
            if exc.status_code in (400, 402) and any(word in message for word in ("credit balance", "spend limit", "billing")):
                return "The model service reported a billing or spending limit. Check your credits and spend limits in Claude Console."
            if exc.status_code == 429:
                return "The model service returned a rate limit. Try later; this does not mean credits are exhausted."
            return f"The model service returned HTTP {exc.status_code}. Check access and service settings. Recorded evidence is preserved."
        return f"This run did not finish ({type(exc).__name__}). Check connection and configuration. Saved evidence is preserved."
    if isinstance(exc, APITimeoutError):
        return "模型请求超时，无法据此判断额度。请检查服务网络；当前证据已保存。"
    if isinstance(exc, APIConnectionError):
        return "无法连接模型 API，尚未收到服务端响应；这不是额度耗尽提示。请检查启动服务的网络权限、代理或连接。当前证据已保存。"
    if isinstance(exc, APIStatusError):
        body = getattr(exc, "body", None)
        error = body.get("error", body) if isinstance(body, dict) else {}
        message = str(error.get("message", "")).lower() if isinstance(error, dict) else ""
        if exc.status_code in (400, 402) and any(word in message for word in ("credit balance", "spend limit", "billing")):
            return "模型服务返回额度或账单限制，请到 Claude Console 核对余额与消费上限。"
        if exc.status_code in (401, 403):
            return "模型服务拒绝访问，请核对 API Key 与账号权限。"
        if exc.status_code == 429:
            return "模型服务返回请求频率限制，请稍后重试；这不等于余额耗尽。"
        return f"模型服务返回 HTTP {exc.status_code}，本轮未完成。当前证据已保存。"
    return f"本轮未完成（{type(exc).__name__}）。请检查网络和配置；已保存的状态仍可查看。不要重复开始同一诊断。"


def valid_thread(thread_id):
    if not isinstance(thread_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", thread_id):
        raise ValueError("会话编号须为 1～80 个字母、数字、下划线或连字符。")


class DashboardService:
    def __init__(self, database=None, runs=None, ticket_store=None, captures=None):
        self.database = Path(database or ROOT / "data/checkpoints/diagnosis.sqlite3")
        self.runs = Path(runs or ROOT / "data/runs")
        self.ticket_store = ticket_store
        self.captures = Path(captures or self.runs.parent / "ros_captures")

    def fetch_ros(self, port=8765):
        return HttpMotionSession(port).export_capture()

    def _save_capture(self, payload, port):
        validate_capture(payload)
        raw = json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
        capture_id = payload["capture_id"]
        path = self.captures / (capture_id + ".json")
        with _guard:
            self.captures.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if path.read_bytes() != raw:
                    raise RosCaptureError("A different payload already exists for this capture ID.")
            else:
                with path.open("xb") as stream:
                    stream.write(raw)
        return {"capture_id": capture_id, "capture_sha256": hashlib.sha256(raw).hexdigest(),
                "port": port, "kind": "wsl_ros2_synthetic_replay"}

    def _saved_motion(self, state):
        metadata = state["source_metadata"]
        capture_id = metadata["capture_id"]
        if not re.fullmatch(r"[0-9a-f]{32}", capture_id):
            raise ValueError("Invalid capture ID.")
        raw = (self.captures / (capture_id + ".json")).read_bytes()
        if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != metadata["capture_sha256"]:
            raise ValueError("Cached ROS capture changed.")
        payload = json.loads(raw)
        captured, rows = validate_capture(payload)
        if captured["observations"] != state["evidence"]:
            raise ValueError("Cached capture differs from this thread's evidence.")
        return {"state": captured, "rows": rows}

    def read(self, thread_id):
        valid_thread(thread_id)
        if not self.database.exists():
            return {"state": {}, "interrupts": [], "runs": []}
        with tracing_context(enabled=False), SqliteSaver.from_conn_string(str(self.database)) as saver:
            snapshot = build_workflow(checkpointer=saver).get_state({"configurable": {"thread_id": thread_id}})
        runs = []
        for path in self.runs.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if record.get("thread_id") == thread_id:
                    runs.append({"run_id": record["run_id"], "trace_url": record.get("trace_url"),
                                 "trace_verified": record.get("trace_verified", False),
                                 "visited_nodes": record.get("visited_nodes", [])})
            except (OSError, ValueError, KeyError):
                continue
        view = {"state": snapshot.values,
                "interrupts": [item.value for task in snapshot.tasks for item in task.interrupts], "runs": runs}
        if snapshot.values.get("data_source") == "wsl_ros":
            try:
                view["motion"] = self._saved_motion(snapshot.values)
            except (ValueError, KeyError, OSError, TypeError):
                view["motion_error"] = True
        return view

    def dependencies(self, scope):
        from anthropic import Anthropic
        from langsmith.wrappers import wrap_anthropic
        from rag_demo.config import load_environment
        from rag_demo.retrieval import KnowledgeIndex
        load_environment()
        return (wrap_anthropic(Anthropic(max_retries=0, timeout=60.)), KnowledgeIndex(applies_to=scope),
                os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"))

    def tracing_client(self):
        from langsmith import Client
        return Client()

    def execute(self, thread_id, *, task_type=None, scenario=None, question=None, ticket=False,
                decision=None, retry=False, on_node=None, output_language=None, data_source=None,
                ros_port=None, expected_capture_id=None):
        valid_thread(thread_id)
        key = str(self.database.resolve()) + ":" + thread_id
        with _guard:
            lock = _locks.setdefault(key, threading.Lock())
        if not lock.acquire(blocking=False):
            raise ValueError("该会话正在执行，请等待完成后刷新。")
        try:
            return self._execute(thread_id, task_type, scenario, question, ticket, decision, retry, on_node, output_language,
                                 data_source, ros_port, expected_capture_id)
        finally:
            lock.release()

    def _execute(self, thread_id, task_type, scenario, question, ticket, decision, retry, on_node, output_language,
                 data_source, ros_port, expected_capture_id):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
        with tracing_context(enabled=False), SqliteSaver.from_conn_string(str(self.database)) as saver:
            snapshot = build_workflow(checkpointer=saver).get_state(config)
            resuming = decision is not None or retry
            if resuming:
                if task_type or scenario or question or ticket or output_language or data_source or ros_port or expected_capture_id:
                    raise ValueError("恢复使用原会话的任务、证据与工单请求。")
                if not snapshot.values or snapshot.values.get("workflow_version") != WORKFLOW_VERSION:
                    raise ValueError("会话不存在或版本已变化，请新建会话。")
                task_type = snapshot.values["task_type"]
            else:
                if snapshot.values:
                    raise ValueError("会话已存在，请载入后继续，或创建新会话。")
                data_source = data_source or "local_json"
                if data_source == "wsl_ros":
                    if task_type != "joint_response" or scenario is not None or not expected_capture_id:
                        raise ValueError("ROS requires joint_response and a checked capture ID, with no local scenario.")
                elif data_source == "local_json":
                    allowed = MOTION_SCENARIOS if task_type == "joint_response" else INIT_SCENARIOS
                    if task_type not in TASK_SCOPES or scenario not in allowed or ros_port or expected_capture_id:
                        raise ValueError("任务与工况不匹配。")
                else:
                    raise ValueError("Unknown data source.")
                if not isinstance(question, str) or not question.strip() or len(question) > 4000:
                    raise ValueError("问题须为 1～4000 个字符。")
            session, source_metadata = None, {}
            if not resuming:
                if data_source == "wsl_ros":
                    session = HttpMotionSession(ros_port or 8765, expected_capture_id=expected_capture_id)
                    source_metadata = self._save_capture(session.export_capture(), ros_port or 8765)
                else:
                    session = MotionSession(scenario) if task_type == "joint_response" else DiagnosticSession(scenario)
            claude, index, model = self.dependencies(TASK_SCOPES[task_type])
            if retry:
                check_retry(snapshot, index.knowledge_version, model)
                invocation = None
            elif resuming:
                mode = check_resume(snapshot, decision, index.knowledge_version, model)
                if mode == "existing_ticket":
                    (self.ticket_store or TicketStore()).get(snapshot.values["ticket"]["ticket_id"])
                    return self.read(thread_id)
                invocation = Command(resume=decision)
            else:
                invocation = initial_state(question.strip(), model, index.knowledge_version, ticket, thread_id, task_type, output_language)
                invocation.update(data_source=data_source, source_metadata=source_metadata)
            graph = build_workflow(claude, index, session, saver, ticket_store=self.ticket_store)
            bound_state = snapshot.values if resuming else invocation
            client = self.tracing_client()
            run_id, visited = uuid4(), []
            record = {"run_id": str(run_id), "thread_id": thread_id, "visited_nodes": visited,
                      "trace_url": None, "trace_verified": False}
            try:
                with tracing_context(enabled=client is not None, client=client):
                    with trace("bench-diagnosis-graph", run_type="chain", run_id=run_id,
                               inputs={"thread_id": thread_id, "mode": "resume" if resuming else "start"},
                               metadata={"thread_id": thread_id, "workflow_version": WORKFLOW_VERSION,
                                         "task_type": task_type, "knowledge_version": index.knowledge_version,
                                         "data_source": bound_state.get("data_source", "local_json"),
                                         "source_metadata": bound_state.get("source_metadata", {})},
                               tags=["streamlit", "synthetic-data", task_type]) as root:
                        for event in graph.stream(invocation, config, stream_mode="updates"):
                            for node, result in event.items():
                                if node != "__interrupt__":
                                    visited.append(node)
                                    if on_node:
                                        on_node(node, result)
                        state = graph.get_state(config).values
                        root.end(outputs={"status": state["status"], "answer": state.get("answer"),
                                          "usage": state["usage"], "visited_nodes": visited})
                if client is not None:
                    client.flush()
                    from rag_demo.tracing import verify_trace
                    try:
                        record["trace_url"] = root.get_url()
                        record["trace_url"] = verify_trace(root, 2, expected_names={"bench-workflow", *visited})
                        record["trace_verified"] = True
                    except Exception:
                        record["trace_note"] = "本次追踪未完成回读验证；请勿为此重复调用模型。"
            finally:
                if client is not None:
                    client.flush()
                record["state"] = graph.get_state(config).values
                self.runs.mkdir(parents=True, exist_ok=True)
                (self.runs / f"ui-{run_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self.read(thread_id)
