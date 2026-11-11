"""Check local presentation evidence and inventory saved cases without API calls."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag_demo.dashboard import DashboardService
from rag_demo.workflow import WORKFLOW_VERSION
from simulator.motion import ROOT as MOTION_ROOT, SCENARIOS, verify_fixture


def main():
    fixture_results = []
    for scenario in SCENARIOS:
        state, rows = verify_fixture(MOTION_ROOT / scenario)
        results = state["observations"]["read_motion_test_results"]["data"]
        fixture_results.append({"scenario": scenario, "sample_count": len(rows),
                                "response_status": results["response_requirement_status"]})
        print(f"FIXTURE: {scenario}: verified {len(rows)} samples")

    threads = set()
    for path in (ROOT / "data/runs").glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            thread = record.get("thread_id") or record.get("state", {}).get("thread_id")
            if thread:
                threads.add(thread)
        except (ValueError, OSError):
            continue

    service, cases, warnings = DashboardService(), [], []
    for thread in sorted(threads):
        try:
            view = service.read(thread)
        except (ValueError, OSError):
            warnings.append(f"Could not read thread {thread}.")
            continue
        state = view["state"]
        if state.get("task_type") != "joint_response" or state.get("workflow_version") != WORKFLOW_VERSION:
            continue
        if state.get("report", {}).get("language") != "en" or state.get("diagnosis_status") != "completed":
            continue
        if state.get("status") not in ("completed", "awaiting_ticket_approval"):
            continue
        conditions = state["evidence"]["read_motion_test_conditions"]["data"]
        results = state["evidence"]["read_motion_test_results"]["data"]
        overshoot = next(m["value"] for m in results["metrics"] if m["metric_id"] == "overshoot_pct")
        source = state.get("data_source", "local_json")
        if source == "wsl_ros" and view.get("motion_error"):
            warnings.append(f"Saved ROS curve failed validation for {thread}; do not substitute JSON.")
            continue
        role = ("main_oscillation" if source == "local_json" and overshoot > 50
                else "missing_load_continuation" if source == "wsl_ros" and conditions["test_context_status"] == "incomplete"
                else "other_english_case")
        traces = [r["trace_url"] for r in view["runs"] if r.get("trace_url") and r.get("trace_verified")]
        cases.append({"role": role, "thread_id": thread, "mode": "verified_historical_run",
                      "source": source, "test_id": conditions["test_id"], "status": state["status"],
                      "overshoot_pct": overshoot, "verified_trace_urls": traces,
                      "has_pending_draft": state.get("status") == "awaiting_ticket_approval"})

    roles = {case["role"] for case in cases}
    missing = sorted({"main_oscillation", "missing_load_continuation"} - roles)
    inventory = {"workflow_version": WORKFLOW_VERSION, "fixtures": fixture_results,
                 "cases": cases, "missing_presentation_roles": missing, "warnings": warnings,
                 "notice": "Local inspection only. No model calls, ROS requests, approvals or workflow resumes."}
    destination = ROOT / "data/presentation/session_inventory.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    for case in cases:
        print(f"CASE: {case['role']}: {case['thread_id']} [{case['source']}; {case['status']}]")
    for warning in warnings:
        print("WARNING: " + warning)
    if missing:
        print("PREPARATION NEEDED: " + ", ".join(missing))
    else:
        print("LOCAL_CASES_READY: both required saved English cases are available")
    print("INVENTORY: data/presentation/session_inventory.json")
    return int(bool(missing))


if __name__ == "__main__":
    raise SystemExit(main())
