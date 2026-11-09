"""Inspect one simulated tool response without network access."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.tools import DiagnosticSession, SCENARIOS, TOOL_DESCRIPTIONS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="healthy")
    parser.add_argument("--tool", choices=TOOL_DESCRIPTIONS, default="read_initialization_status")
    parser.add_argument("--bench-id", default="BENCH-001")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.tool != "read_diagnostic_log":
        parser.error("--limit applies only to read_diagnostic_log")
    arguments = {"bench_id": args.bench_id}
    if args.limit is not None:
        arguments["limit"] = args.limit
    try:
        session = DiagnosticSession(args.scenario)
    except ValueError as exc:
        parser.exit(1, str(exc) + "\n")
    result = session.call(args.tool, arguments)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
