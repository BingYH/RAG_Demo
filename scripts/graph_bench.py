"""Run or resume the LangGraph bench diagnosis workflow."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag_demo.workflow import WORKFLOW_VERSION, TASK_SCOPES, build_workflow, initial_state
from simulator.motion import SCENARIOS as MOTION_SCENARIOS
from rag_demo.tickets import TicketStore, content_hash, render_draft, validate_decision, verify_approval


def check_versions(snapshot, knowledge_version, model):
    state = snapshot.values
    if not state:
        raise ValueError("Thread not found; start a new thread first.")
    if state.get("workflow_version") != WORKFLOW_VERSION:
        raise ValueError("Workflow version changed; start a new thread instead of reusing this checkpoint.")
    if state.get("knowledge_version") != knowledge_version or state.get("model") != model:
        raise ValueError("Knowledge or model version changed; restore the original settings or start a new thread.")


def check_resume(snapshot, reply, knowledge_version, model):
    check_versions(snapshot, knowledge_version, model)
    state = snapshot.values
    if state.get("status") == "awaiting_input" and "clarify" in snapshot.next:
        if not isinstance(reply, str) or not reply.strip() or len(reply) > 2000:
            raise ValueError("Use --reply with 1 to 2000 characters for clarification.")
        return "clarification"
    if state.get("status") == "awaiting_ticket_approval" and "await_ticket_approval" in snapshot.next:
        validate_decision(state["ticket_draft"], reply)
        return "ticket_decision"
    if state.get("status") == "ticket_created" and isinstance(reply, dict) and reply.get("action") == "approve":
        validate_decision(state["ticket_draft"], reply)
        return "existing_ticket"
    raise ValueError("This thread is not waiting for input; completed threads cannot be resumed.")


def check_retry(snapshot, knowledge_version, model):
    check_versions(snapshot, knowledge_version, model)
    state = snapshot.values
    if state.get("status") != "running" or tuple(snapshot.next) != ("create_ticket",):
        raise ValueError("--retry is limited to interrupted or failed, already-approved local ticket creation.")
    verify_approval(state["thread_id"], state["ticket_draft"], state["ticket_approval"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--thread-id", help="Name a new thread; defaults to a new UUID")
    group.add_argument("--resume", metavar="THREAD_ID", help="Resume a paused thread")
    group.add_argument("--retry", metavar="THREAD_ID", help="Retry already-approved local ticket creation after an execution failure")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--reply", help="User context for a paused thread; does not change fixture observations")
    actions.add_argument("--approve", metavar="DRAFT_HASH", help="Approve the exact draft hash printed for review")
    actions.add_argument("--cancel", action="store_true", help="Cancel the pending ticket draft")
    actions.add_argument("--edit-draft", metavar="JSON_FILE", help="Edit allowed text fields; requires --draft-hash")
    parser.add_argument("--draft-hash", help="Expected current hash for --edit-draft")
    parser.add_argument("--ticket", action="store_true", help="Request a local support-ticket draft after diagnosis")
    parser.add_argument("--task", choices=TASK_SCOPES, help="New thread task; defaults to initialization")
    parser.add_argument("--scenario", choices=("healthy", "version_mismatch", "connection_timeout", *MOTION_SCENARIOS))
    parser.add_argument("--question")
    parser.add_argument("--show-graph", action="store_true", help="Print Mermaid without API calls or database access")
    args = parser.parse_args()
    if args.show_graph:
        print(build_workflow().get_graph().draw_mermaid())
        return
    if (args.resume or args.retry) and (args.scenario or args.question or args.ticket or args.task):
        parser.error("Resume/retry uses the saved question, snapshot and ticket request.")
    if args.scenario and ((args.scenario in MOTION_SCENARIOS) != (args.task == "joint_response")):
        parser.error("Motion scenarios require --task joint_response; initialization uses its own scenarios.")
    has_action = args.reply is not None or args.approve is not None or args.cancel or args.edit_draft is not None
    if has_action and not args.resume:
        parser.error("A user reply or ticket decision requires --resume")
    if args.resume and not has_action:
        parser.error("--resume requires --reply, --approve, --cancel or --edit-draft")
    if bool(args.edit_draft) != bool(args.draft_hash):
        parser.error("--edit-draft and --draft-hash must be supplied together")
    decision = args.reply
    if args.approve is not None:
        decision = {"action": "approve", "draft_hash": args.approve}
    elif args.cancel:
        decision = {"action": "cancel"}
    elif args.edit_draft:
        try:
            edits = json.loads(Path(args.edit_draft).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            parser.error("Cannot read --edit-draft as a JSON object.")
        decision = {"action": "edit", "draft_hash": args.draft_hash, "edits": edits}
    thread_id = args.resume or args.retry or args.thread_id or uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", thread_id):
        parser.error("Thread ID must contain 1 to 80 letters, numbers, underscores or hyphens.")
    question = args.question or ("BENCH-001 单关节位置响应测试，请根据记录的条件、配置与指标帮助分析。"
                                 if args.task == "joint_response" else "BENCH-001 更新后台架初始化失败，请帮我排查。")
    if not question.strip() or len(question) > 4000:
        parser.error("Question must contain 1 to 4000 characters.")
    from rag_demo.config import load_environment
    load_environment()
    from anthropic import Anthropic
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command
    from langsmith import Client, trace, tracing_context
    from langsmith.wrappers import wrap_anthropic
    from rag_demo.retrieval import KnowledgeIndex
    from rag_demo.tracing import verify_trace
    from simulator.tools import DiagnosticSession
    from simulator.motion_tools import MotionSession

    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
    client, run_id = None, uuid4()
    directory = ROOT / "data" / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    print("Thread ID:", thread_id, flush=True)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
    visited, payloads = [], []
    with SqliteSaver.from_conn_string(str(directory / "diagnosis.sqlite3")) as saver:
        with tracing_context(enabled=False):
            snapshot = build_workflow(checkpointer=saver).get_state(config)
        if args.resume or args.retry:
            if not snapshot.values or snapshot.values.get("workflow_version") != WORKFLOW_VERSION:
                raise ValueError("Thread missing or workflow version changed; start a new thread.")
            task_type = snapshot.values["task_type"]
        else:
            if snapshot.values:
                raise ValueError("Thread already exists; use --resume for a paused thread or choose a new ID.")
            task_type = args.task or "initialization"
        index = KnowledgeIndex(applies_to=TASK_SCOPES[task_type])
        print("Task:", task_type, "Knowledge version:", index.knowledge_version, flush=True)
        if args.resume:
            mode = check_resume(snapshot, decision, index.knowledge_version, model)
            if mode == "existing_ticket":
                ticket = TicketStore().get(snapshot.values["ticket"]["ticket_id"])
                if ticket["thread_id"] != thread_id or ticket["draft_hash"] != decision["draft_hash"]:
                    raise ValueError("Stored ticket does not match this approved thread and draft.")
                print("Local ticket already exists:", ticket["ticket_id"], "No duplicate was created.", flush=True)
                return
            invocation = Command(resume=decision.strip() if isinstance(decision, str) else decision)
        elif args.retry:
            check_retry(snapshot, index.knowledge_version, model)
            invocation = None
        else:
            if snapshot.values:
                raise ValueError("Thread already exists; use --resume for a paused thread or choose a new ID.")
            invocation = initial_state(question, model, index.knowledge_version,
                                       ticket_requested=args.ticket, thread_id=thread_id, task_type=task_type)
        session = None
        if not args.resume and not args.retry:
            session = (MotionSession(args.scenario or MOTION_SCENARIOS[0]) if task_type == "joint_response"
                       else DiagnosticSession(args.scenario or "connection_timeout"))
        claude = wrap_anthropic(Anthropic(max_retries=0, timeout=60.0))
        with tracing_context(enabled=False):
            graph = build_workflow(claude, index, session, saver)
        client = Client()
        try:
            with tracing_context(enabled=True, client=client):
                with trace("bench-diagnosis-graph", run_type="chain", run_id=run_id,
                           inputs={"thread_id": thread_id, "mode": "resume" if args.resume else ("retry" if args.retry else "start")},
                           metadata={"thread_id": thread_id, "workflow_version": WORKFLOW_VERSION,
                                     "knowledge_version": index.knowledge_version, "task_type": task_type},
                           tags=["langgraph", "synthetic-data", task_type]) as root:
                    for event in graph.stream(invocation, config, stream_mode="updates"):
                        for node, result in event.items():
                            if node == "__interrupt__":
                                payloads = [item.value for item in result]
                                print("Workflow paused:", ", ".join(p["kind"] for p in payloads), flush=True)
                            else:
                                visited.append(node)
                                print("Node:", node, flush=True)
                                if result.get("route"):
                                    print("  Route:", result["route"], flush=True)
                                if result.get("error"):
                                    print("  Reason:", result["error"], flush=True)
                    state = graph.get_state(config).values
                    root.end(outputs={"status": state["status"], "answer": state.get("answer"),
                        "usage": state["usage"], "visited_nodes": visited, "interrupts": payloads,
                        "evidence_reviews": state["evidence_reviews"], "ticket": state.get("ticket")})
        finally:
            client.flush()
    output = ROOT / "data" / "runs"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"graph-{run_id}.json").write_text(json.dumps(
        {"run_id": str(run_id), "thread_id": thread_id, "visited_nodes": visited,
         "interrupts": payloads, "state": state}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if payloads:
        for payload in payloads:
            if payload["kind"] == "clarification":
                print("\n" + payload["question"], flush=True)
                print(f'Resume: .\\.venv\\Scripts\\python.exe scripts/graph_bench.py --resume {thread_id} --reply "你的说明"', flush=True)
            else:
                if state.get("answer"):
                    print("\n" + state["answer"], flush=True)
                print("\n" + render_draft(payload["draft"]), flush=True)
                draft_dir = ROOT / "data" / "tickets" / "drafts"
                draft_dir.mkdir(parents=True, exist_ok=True)
                draft_file = draft_dir / (payload["draft_hash"] + ".json")
                draft_file.write_text(json.dumps(payload["draft"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("Full draft JSON:", draft_file, flush=True)
                print("Draft hash:", payload["draft_hash"], flush=True)
                print(f'Approve: .\\.venv\\Scripts\\python.exe scripts/graph_bench.py --resume {thread_id} --approve {payload["draft_hash"]}', flush=True)
                print(f'Edit: .\\.venv\\Scripts\\python.exe scripts/graph_bench.py --resume {thread_id} --edit-draft edits.json --draft-hash {payload["draft_hash"]}', flush=True)
                print(f'Cancel: .\\.venv\\Scripts\\python.exe scripts/graph_bench.py --resume {thread_id} --cancel', flush=True)
            print(payload["note"], flush=True)
    else:
        print("\n" + state["answer"], flush=True)
        if state.get("ticket"):
            print("Ticket file:", state["ticket"]["file_path"], flush=True)
    print("\nStatus:", state["status"], "Total thread usage:", state["usage"], flush=True)
    try:
        print("Trace URL:", verify_trace(root, 2, expected_names={"bench-workflow", *visited}), flush=True)
    except Exception as exc:
        print("Trace read-back not verified:", type(exc).__name__, "Run ID:", run_id, flush=True)
        raise SystemExit(2) from None
    if state["status"] == "escalated":
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        raise SystemExit(1) from None
