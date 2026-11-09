"""Run the local knowledge + Claude + diagnostic tools prototype."""

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_demo.retrieval import KnowledgeIndex
from simulator.tools import DiagnosticSession, SCENARIOS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="connection_timeout")
    parser.add_argument("--question", default="BENCH-001 更新后台架初始化失败，请帮我排查。")
    parser.add_argument("--index-only", action="store_true", help="Build/query local knowledge without API calls")
    parser.add_argument("--query", default="connection timeout configured endpoint registration address discrepancy")
    args = parser.parse_args()
    print("Preparing local knowledge index (first use downloads an embedding model)...", flush=True)
    index = KnowledgeIndex()
    print("Knowledge version:", index.knowledge_version, "chunks:", index.chunk_count, flush=True)
    if args.index_only:
        print(json.dumps(index.search(args.query), indent=2, ensure_ascii=False))
        return
    if not args.question.strip() or len(args.question) > 4000:
        parser.error("Question must be 1 to 4000 characters.")
    from rag_demo.config import load_environment
    load_environment()
    from anthropic import Anthropic
    from langsmith import Client, trace, tracing_context
    from langsmith.wrappers import wrap_anthropic
    from rag_demo.diagnosis import run_diagnosis
    from rag_demo.tracing import verify_trace

    session = DiagnosticSession(args.scenario)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
    claude = wrap_anthropic(Anthropic(max_retries=0, timeout=60.0))
    client = Client()
    run_id = uuid4()
    print("Model:", model, flush=True)
    try:
        with tracing_context(enabled=True, client=client):
            with trace("bench-diagnosis", run_type="chain", run_id=run_id,
                       inputs={"question": args.question, "bench_id": "BENCH-001"},
                       metadata={"knowledge_version": index.knowledge_version, "prompt_version": "diagnosis-v3-evidence-review"},
                       tags=["synthetic-data", "read-only-prototype"]) as root:
                result = run_diagnosis(claude, session, index, args.question, model)
                root.end(outputs=result)
    finally:
        client.flush()
    print("\n" + result["answer"], flush=True)
    print("\nUsage:", result["usage"], flush=True)
    # Persist only synthetic inputs, outputs and tool summaries, never credentials.
    output = Path(__file__).resolve().parents[1] / "data" / "runs"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{run_id}.json").write_text(json.dumps(
        {"run_id": str(run_id), "question": args.question, **result}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    try:
        url = verify_trace(root, result["trace_expected_steps"])
        print("Trace URL:", url, flush=True)
    except Exception as exc:
        print("Diagnosis completed, but trace read-back could not be verified:", type(exc).__name__, flush=True)
        print("Run ID:", run_id, "Check LangSmith; avoid rerunning solely to repeat verification.", flush=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        raise SystemExit(1) from None
