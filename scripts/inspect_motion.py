"""Verify and inspect a saved motion fixture without LLM calls."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.motion import ROOT, SCENARIOS, plot_response, verify_fixture
from simulator.motion_tools import MotionSession, TOOL_DESCRIPTIONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[0])
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--tool", choices=TOOL_DESCRIPTIONS)
    parser.add_argument("--bench-id", default="BENCH-001")
    parser.add_argument("--test-id")
    args = parser.parse_args()
    if not args.tool and (args.test_id or args.bench_id != "BENCH-001"):
        parser.error("--bench-id and --test-id require --tool")
    try:
        session = MotionSession(args.scenario)
        if args.tool:
            result = session.call(args.tool, {"bench_id": args.bench_id, "test_id": args.test_id or session.test_id})
            print(json.dumps(result, indent=2))
            if result["status"] == "error":
                raise SystemExit(1)
        else:
            state, _ = verify_fixture(ROOT / args.scenario)
            print(json.dumps(state, indent=2))
        if args.plot:
            state, rows = verify_fixture(ROOT / args.scenario)
            output = Path(__file__).resolve().parents[1] / "data/motion_reports" / f"{state['test_id']}.png"
            plot_response(state, rows, output)
            print(f"Plot: {output}")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Motion fixture validation failed: {exc}\n")


if __name__ == "__main__":
    main()
