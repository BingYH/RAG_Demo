"""Run the two fixed evidence-review variants (uses Claude API credits)."""

import json
import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("version_mismatch_review", "joint_response_review"), default="version_mismatch_review")
    args = parser.parse_args()
    from rag_demo.config import load_environment
    load_environment()
    from anthropic import Anthropic
    from langsmith import Client, trace, tracing_context
    from langsmith.wrappers import wrap_anthropic
    from rag_demo.facts import extract_facts
    from rag_demo.retrieval import load_chunks
    from rag_demo.review import review_report
    from simulator.tools import DiagnosticSession, TOOL_DESCRIPTIONS
    from simulator.motion_tools import MotionSession, TOOL_DESCRIPTIONS as MOTION_TOOLS
    from rag_demo.workflow import TASK_SCOPES
    from rag_demo.tracing import verify_trace

    root = Path(__file__).resolve().parents[1]
    case = json.loads((root / "evaluation/cases" / (args.case + ".json")).read_text(encoding="utf-8"))
    motion = case.get("task_type") == "joint_response"
    session = MotionSession(case["scenario"]) if motion else DiagnosticSession(case["scenario"])
    facts = {}
    for name in (MOTION_TOOLS if motion else TOOL_DESCRIPTIONS):
        arguments = {"bench_id": "BENCH-001"}
        if motion:
            arguments["test_id"] = session.test_id
        for fact in extract_facts(name, session.call(name, arguments)):
            facts[fact["fact_id"]] = fact
    chunks = {chunk["id"]: chunk for chunk in load_chunks(root / "knowledge",
              applies_to=TASK_SCOPES[case.get("task_type", "initialization")])}
    claude = wrap_anthropic(Anthropic(max_retries=0, timeout=60.0))
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
    client, run_id = Client(), uuid4()
    results = []
    try:
        with tracing_context(enabled=True, client=client):
            with trace("review-regression", run_type="chain", run_id=run_id,
                       inputs={"case_id": case["case_id"]}, tags=["evaluation", "synthetic-data"]) as run:
                for variant in case["variants"]:
                    # Expected outcomes and scenario labels are not sent to the reviewer.
                    decision = review_report(claude, model, variant["report"], facts, chunks)
                    codes = {issue["code"] for issue in decision["issues"]}
                    passed = (decision["passed"] == variant["expected_passed"] and
                              set(variant["expected_issue_codes"]) <= codes)
                    results.append({"variant": variant["name"], "check_passed": passed, "decision": decision})
                    print(variant["name"], "PASS" if passed else "FAIL", sorted(codes), flush=True)
                run.end(outputs={"results": results})
    finally:
        client.flush()
    output = root / "evaluation/results"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"review-{run_id}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Run ID:", run_id)
    print("Trace URL:", verify_trace(run, 2, expected_names={"evidence_review"}))
    if not all(r["check_passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
