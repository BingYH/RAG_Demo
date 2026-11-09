"""Session-bound read-only tools; no networking, processes or model calls."""

import copy
import hashlib
import json
from pathlib import Path

SCENARIOS = ("healthy", "version_mismatch", "connection_timeout")
TOOL_DESCRIPTIONS = {
    "read_bench_inventory": "Read registered bench identity and expected configuration; registration is not a live observation.",
    "read_runtime_config": "Read installed client, loaded endpoint, supported demo protocols and recorded changes.",
    "read_connection_observations": "Read recorded link, ping and handshake observations for the configured endpoint.",
    "read_initialization_status": "Read the recorded initialization stage, error and available controller state observations.",
    "read_diagnostic_log": "Read the most recent recorded diagnostic events in chronological order.",
}


def tool_specs() -> list[dict]:
    """Anthropic-compatible definitions; scenario selection is never a tool input."""
    specs = []
    for name, description in TOOL_DESCRIPTIONS.items():
        properties = {"bench_id": {"type": "string", "enum": ["BENCH-001"]}}
        if name == "read_diagnostic_log":
            properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 100,
                                   "default": 20}
        specs.append({"name": name, "description": description, "input_schema": {
            "type": "object", "properties": properties, "required": ["bench_id"],
            "additionalProperties": False,
        }})
    return specs


class DiagnosticSession:
    """Load a fixture once; all calls share its immutable in-memory snapshot.

    Construct one instance per workflow thread. The application selects the
    scenario before binding tools. Never expose the constructor to the model.
    """

    def __init__(self, scenario: str):
        if scenario not in SCENARIOS:
            raise ValueError("Unknown diagnostic scenario.")
        directory = Path(__file__).resolve().parent / "scenarios" / scenario
        try:
            state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
            events = [json.loads(line) for line in
                      (directory / "diagnostic.log").read_text(encoding="utf-8").splitlines()]
            self._validate_snapshot(state, events)
        except (OSError, ValueError, KeyError, TypeError):
            # Keep local paths and fixture labels out of errors passed to agents.
            raise ValueError("Diagnostic snapshot could not be loaded or validated.") from None
        self._state = copy.deepcopy(state)
        self._events = copy.deepcopy(events)

    @staticmethod
    def _validate_snapshot(state: dict, events: list) -> None:
        if state["schema_version"] != "1.0" or state["bench_id"] != "BENCH-001":
            raise ValueError("Unsupported snapshot.")
        observations = state["observations"]
        expected = set(TOOL_DESCRIPTIONS) - {"read_diagnostic_log"}
        if set(observations) != expected or not events:
            raise ValueError("Incomplete snapshot.")
        for envelope in [*observations.values(), state["log_stream"]]:
            if (envelope["snapshot_id"] != state["snapshot_id"] or
                    envelope["bench_id"] != state["bench_id"] or
                    envelope["source_type"] != "synthetic"):
                raise ValueError("Inconsistent snapshot.")
        attempt = observations["read_runtime_config"]["data"]["startup_attempt_id"]
        if any(e["startup_attempt_id"] != attempt for e in events):
            raise ValueError("Inconsistent log attempt.")
        if [e["timestamp"] for e in events] != sorted(e["timestamp"] for e in events):
            raise ValueError("Unordered log events.")

    def _error(self, code: str, message: str) -> dict:
        token = hashlib.sha256(code.encode()).hexdigest()[:8]
        return {"bench_id": self._state["bench_id"],
                "snapshot_id": self._state["snapshot_id"],
                "evidence_id": f"ERR-{self._state['snapshot_id']}-{token}",
                "source_type": "synthetic", "observation_origin": "tool_validation",
                "observed_at": self._state["snapshot_at"], "status": "error",
                "data": None, "unavailable_fields": [],
                "error": {"code": code, "message": message}}

    def call(self, tool_name: str, arguments: dict) -> dict:
        """Validate a model tool request and return only its evidence envelope."""
        if not isinstance(tool_name, str) or tool_name not in TOOL_DESCRIPTIONS:
            return self._error("UNKNOWN_TOOL", "Requested diagnostic tool is unavailable.")
        if not isinstance(arguments, dict):
            return self._error("INVALID_ARGUMENTS", "Tool arguments must be an object.")
        allowed = {"bench_id", "limit"} if tool_name == "read_diagnostic_log" else {"bench_id"}
        if set(arguments) - allowed or "bench_id" not in arguments:
            return self._error("INVALID_ARGUMENTS", "Required or allowed tool arguments do not match.")
        if arguments["bench_id"] != self._state["bench_id"]:
            return self._error("UNKNOWN_BENCH", "The requested bench is not bound to this session.")
        if tool_name != "read_diagnostic_log":
            return copy.deepcopy(self._state["observations"][tool_name])
        limit = arguments.get("limit", 20)
        if type(limit) is not int or not 1 <= limit <= 100:
            return self._error("INVALID_LIMIT", "Log limit must be an integer from 1 to 100.")
        result = copy.deepcopy(self._state["log_stream"])
        result["evidence_id"] += f"-n{limit}"
        result["data"] = {"events": copy.deepcopy(self._events[-limit:])}
        return result

    def read_bench_inventory(self, bench_id: str) -> dict:
        return self.call("read_bench_inventory", {"bench_id": bench_id})

    def read_runtime_config(self, bench_id: str) -> dict:
        return self.call("read_runtime_config", {"bench_id": bench_id})

    def read_connection_observations(self, bench_id: str) -> dict:
        return self.call("read_connection_observations", {"bench_id": bench_id})

    def read_initialization_status(self, bench_id: str) -> dict:
        return self.call("read_initialization_status", {"bench_id": bench_id})

    def read_diagnostic_log(self, bench_id: str, limit: int = 20) -> dict:
        return self.call("read_diagnostic_log", {"bench_id": bench_id, "limit": limit})
