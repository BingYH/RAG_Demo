"""Validate authored diagnostic fixtures without a model or network access."""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(directory: Path) -> None:
    state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in
              (directory / "diagnostic.log").read_text(encoding="utf-8").splitlines()]
    observations = state["observations"]
    config = observations["read_runtime_config"]["data"]
    connection = observations["read_connection_observations"]["data"]
    init = observations["read_initialization_status"]["data"]
    assert len(observations) == 4
    evidence_ids = set()
    for envelope in [*observations.values(), state["log_stream"]]:
        assert envelope["snapshot_id"] == state["snapshot_id"]
        assert envelope["bench_id"] == state["bench_id"] == "BENCH-001"
        assert envelope["source_type"] == "synthetic"
        assert envelope["evidence_id"] not in evidence_ids
        evidence_ids.add(envelope["evidence_id"])
        observed_at = datetime.fromisoformat(envelope["observed_at"])
        assert observed_at.tzinfo is not None
        assert observed_at <= datetime.fromisoformat(state["snapshot_at"])
        assert envelope["status"] == ("partial" if envelope["unavailable_fields"] else "ok")
        for unavailable in envelope["unavailable_fields"]:
            value = envelope["data"]
            for field in unavailable["field"].split("."):
                value = value[field]
            assert value is None
    assert config["target_ip"] == connection["target_ip"]
    assert config["execution_mode"] == "fixture"
    assert connection["startup_attempt_id"] == init["startup_attempt_id"] == config["startup_attempt_id"]
    ping = connection["ping"]
    assert 0 <= ping["received"] <= ping["sent"]
    if ping["received"] == 0:
        assert ping["rtt_ms"] is None
        assert connection["controller_version"] is None
        assert connection["reported_protocol"] is None
        assert connection["handshake_status"] == "not_attempted"
        assert init["error_code"] == "DEMO_CONNECT_TIMEOUT"
    if connection["handshake_status"] == "rejected":
        assert connection["reported_protocol"] not in config["supported_protocols"]
        assert init["failed_stage"] == "handshake_accepted"
        assert init["error_code"] == "DEMO_PROTOCOL_MISMATCH"
    if init["status"] == "ready":
        assert connection["handshake_status"] == "accepted"
        assert connection["reported_protocol"] in config["supported_protocols"]
        assert init["state_stream"]["valid_records"] > 0
        assert init["error_code"] is None
        assert init["last_completed_stage"] == "diagnostic_ready"
    else:
        assert init["state_stream"]["valid_records"] is None
        assert any(e.get("error_code") == init["error_code"] for e in events)
    assert init["ros2_nodes"] is None
    times = [datetime.fromisoformat(e["timestamp"]) for e in events]
    assert times == sorted(times)
    assert times[-1] == datetime.fromisoformat(state["snapshot_at"])
    assert len({e["event_id"] for e in events}) == len(events)
    assert all(e["startup_attempt_id"] == config["startup_attempt_id"] for e in events)
    serialized = json.dumps(state) + json.dumps(events)
    assert all(label not in serialized for label in
               ("healthy", "version_mismatch", "connection_timeout", "root_cause", "expected_behavior"))


if __name__ == "__main__":
    fixtures = sorted((ROOT / "simulator" / "scenarios").glob("*/state.json"))
    assert len(fixtures) == 3, "Expected three initial fixtures"
    for fixture in fixtures:
        validate(fixture.parent)
        print("PASS:", fixture.parent.name)
