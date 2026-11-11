"""Bind observations to fields and render facts without model-written values."""

import copy
import json

from rag_demo.ui_i18n import translate

from pydantic import BaseModel, ConfigDict, Field

# Labels belong to the application; values always come from the named tool field.
FIELDS = {
    "read_bench_inventory": {
        "registered_controller_address": (translate('Registered controller address', 'zh'), "Registered controller address"),
        "expected_client_version": (translate('Registered expected client version', 'zh'), "Registered expected client version"),
        "expected_controller_version": (translate('Registered expected controller version', 'zh'), "Registered expected controller version"),
    },
    "read_runtime_config": {
        "client_version": (translate('Installed client version', 'zh'), "Installed client version"),
        "supported_protocols": (translate('Client supported protocols', 'zh'), "Client supported protocols"),
        "target_ip": (translate('Loaded target address', 'zh'), "Loaded target address"),
        "config_revision": (translate('Loaded configuration revision', 'zh'), "Loaded configuration revision"),
        "workstation_address": (translate('Workstation address', 'zh'), "Workstation address"),
        "change_records": (translate('Recorded configuration or software changes', 'zh'), "Recorded configuration or software changes"),
    },
    "read_connection_observations": {
        "link_up": (translate('Local link up', 'zh'), "Local link up"),
        "ping": (translate('Configured endpoint ping observation', 'zh'), "Configured endpoint ping observation"),
        "handshake_status": (translate('Observed handshake status', 'zh'), "Observed handshake status"),
        "controller_version": (translate('Controller version observed during handshake', 'zh'), "Controller version observed during handshake"),
        "reported_protocol": (translate('Controller protocol observed during handshake', 'zh'), "Controller protocol observed during handshake"),
    },
    "read_initialization_status": {
        "last_completed_stage": (translate('Last completed initialization stage', 'zh'), "Last completed initialization stage"),
        "failed_stage": (translate('Failed initialization stage', 'zh'), "Failed initialization stage"),
        "error_code": (translate('Initialization error code', 'zh'), "Initialization error code"),
        "external_interface_enabled": (translate('External interface enabled', 'zh'), "External interface enabled"),
        "state_stream.valid_records": (translate('Valid state records in observation window', 'zh'), "Valid state records in observation window"),
        "ros2_nodes": (translate('ROS 2 node observations', 'zh'), "ROS 2 node observations"),
    },
}

FIELDS.update({
    "read_motion_test_conditions": {
        "test_id": (translate('Recorded motion test ID', 'zh'), "Recorded motion test ID"),
        "joint_id": (translate('Tested abstract joint', 'zh'), "Tested abstract joint"),
        "procedure_id": (translate('Recorded test procedure', 'zh'), "Recorded test procedure"),
        "execution_mode": (translate('Motion test execution mode', 'zh'), "Motion test execution mode"),
        "action": (translate('Recorded target action (rad, s)', 'zh'), "Recorded target action (rad, s)"),
        "observation_window_s": (translate('Motion observation window (s)', 'zh'), "Motion observation window (s)"),
        "sample_period_s": (translate('Trajectory sample period (s)', 'zh'), "Trajectory sample period (s)"),
        "control_period_s": (translate('Simulation control period (s)', 'zh'), "Simulation control period (s)"),
        "payload_record": (translate('Current payload and fixture record', 'zh'), "Current payload and fixture record"),
        "equivalent_inertia": (translate('Recorded current equivalent inertia', 'zh'), "Recorded current equivalent inertia"),
        "test_context_status": (translate('Recorded test context completeness', 'zh'), "Recorded test context completeness"),
        "registered_baseline.payload_id": (translate('Registered baseline payload', 'zh'), "Registered baseline payload"),
        "registered_baseline.equivalent_inertia_kg_m2": (translate('Registered baseline inertia (kg*m^2)', 'zh'), "Registered baseline inertia (kg*m^2)"),
    },
    "read_control_configuration": {
        "mode": (translate('Recorded control mode', 'zh'), "Recorded control mode"),
        "kp": (translate('Recorded Kp (N*m/rad)', 'zh'), "Recorded Kp (N*m/rad)"),
        "ki": (translate('Recorded Ki (integral disabled)', 'zh'), "Recorded Ki (integral disabled)"),
        "kd": (translate('Recorded Kd (N*m*s/rad)', 'zh'), "Recorded Kd (N*m*s/rad)"),
        "torque_limit_nm": (translate('Recorded symmetric torque limit (N*m)', 'zh'), "Recorded symmetric torque limit (N*m)"),
        "config_revision": (translate('Recorded control configuration revision', 'zh'), "Recorded control configuration revision"),
        "change_records": (translate('Recorded control configuration changes', 'zh'), "Recorded control configuration changes"),
        "registered_baseline.kp": (translate('Registered baseline Kp', 'zh'), "Registered baseline Kp"),
        "registered_baseline.ki": (translate('Registered baseline Ki', 'zh'), "Registered baseline Ki"),
        "registered_baseline.kd": (translate('Registered baseline Kd', 'zh'), "Registered baseline Kd"),
    },
    "read_motion_test_results": {
        "metrics_version": (translate('Motion metrics calculation version', 'zh'), "Motion metrics calculation version"),
        "model_version": (translate('Offline simulation model version', 'zh'), "Offline simulation model version"),
        "trajectory_id": (translate('Input trajectory ID', 'zh'), "Input trajectory ID"),
        "trajectory_sha256": (translate('Input trajectory SHA256', 'zh'), "Input trajectory SHA256"),
        "sample_count": (translate('Verified trajectory sample count', 'zh'), "Verified trajectory sample count"),
        "data_integrity": (translate('Trajectory completeness', 'zh'), "Trajectory completeness"),
        "response_requirement_status": (translate('Response demo requirement result', 'zh'), "Response demo requirement result"),
        "metrics.overshoot_pct": (translate('Overshoot metric and demo requirement comparison', 'zh'), "Overshoot metric and demo requirement comparison"),
        "metrics.settling_time_s": (translate('Settling-time metric and demo requirement comparison', 'zh'), "Settling-time metric and demo requirement comparison"),
        "metrics.steady_state_error_rad": (translate('Final-window mean error and demo requirement comparison', 'zh'), "Final-window mean error and demo requirement comparison"),
        "metrics.peak_abs_error_rad": (translate('Peak absolute error (informational)', 'zh'), "Peak absolute error (informational)"),
        "metrics.saturation_fraction": (translate('Sampled output saturation fraction (informational)', 'zh'), "Sampled output saturation fraction (informational)"),
    },
})


def extract_facts(tool_name: str, envelope: dict) -> list[dict]:
    """Only returned, successful observations can enter the fact registry."""
    if envelope.get("status") not in ("ok", "partial"):
        return []
    facts = []
    unavailable = {item["field"]: item["reason"] for item in envelope["unavailable_fields"]}
    for field, labels in FIELDS.get(tool_name, {}).items():
        value = envelope["data"]
        try:
            for part in field.split("."):
                if isinstance(value, list):
                    matches = [item for item in value if isinstance(item, dict) and item.get("metric_id") == part]
                    if len(matches) != 1:
                        raise KeyError(part)
                    value = matches[0]
                else:
                    value = value[part]
        except (KeyError, TypeError):
            continue  # A missing field is not an observed null value.
        facts.append({
            "fact_id": f"{envelope['evidence_id']}::{field}",
            "tool": tool_name, "field": field, "value": copy.deepcopy(value),
            "evidence_id": envelope["evidence_id"], "snapshot_id": envelope["snapshot_id"],
            "observed_at": envelope["observed_at"],
            "origin": "asset_registry" if field.startswith("registered_baseline.") else envelope["observation_origin"],
            "unavailable_reason": unavailable.get(field), "labels": list(labels),
        })
        if tool_name == "read_motion_test_results":
            facts[-1]["derivation"] = {key: envelope["data"][key] for key in
                ("trajectory_id", "trajectory_sha256", "metrics_version", "model_version", "procedure_id")}
        if envelope.get("transport"):
            facts[-1]["transport"] = copy.deepcopy(envelope["transport"])
    return facts


class Interpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1800)
    fact_ids: list[str] = Field(min_length=1, max_length=24)
    chunk_ids: list[str] = Field(min_length=1, max_length=6)


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = Field(pattern="^(zh|en)$")
    fact_ids: list[str] = Field(min_length=1, max_length=24)
    interpretations: list[Interpretation] = Field(min_length=1, max_length=5)
    questions: list[str] = Field(max_length=5)
    next_steps: list[str] = Field(min_length=1, max_length=5)


SUBMIT_TOOL = {"name": "submit_analysis", "description":
    "Submit the final diagnosis after diagnostic and knowledge tools. Select exact fact_ids for the Facts section; "
    "never supply fact text, labels, values or evidence IDs yourself. For each interpretation select supporting "
    "fact_ids and chunk_ids. Text fields must not contain inline citations; the application adds them. "
    "Call this tool alone, after gathering evidence. This submits a report, not a support ticket.",
    "input_schema": Analysis.model_json_schema()}


def render_analysis(payload: dict, facts: dict[str, dict], chunk_ids: set[str]) -> tuple[str, dict]:
    report = Analysis.model_validate(payload)
    selected = set(report.fact_ids)
    for claim in report.interpretations:
        selected.update(claim.fact_ids)
        if not set(claim.chunk_ids) <= chunk_ids:
            raise ValueError("Interpretation references a knowledge chunk not returned.")
    if not selected <= facts.keys():
        raise ValueError("Report references a fact not returned.")
    if len({facts[f]["snapshot_id"] for f in selected}) != 1:
        raise ValueError("Report mixes observations from different snapshots.")
    texts = [c.text for c in report.interpretations] + report.questions + report.next_steps
    if any("[EV-" in text or "::c" in text for text in texts):
        raise ValueError("Text must not supply inline observation or chunk citations.")
    # Always show current versus registered values when either side is mentioned.
    # Unknown observed controller values remain distinct from registry expectations.
    fields = {(f["tool"], f["field"]): fid for fid, f in facts.items()}
    pairs = [
        (("read_runtime_config", "client_version"), ("read_bench_inventory", "expected_client_version")),
        (("read_connection_observations", "controller_version"), ("read_bench_inventory", "expected_controller_version")),
        (("read_runtime_config", "target_ip"), ("read_bench_inventory", "registered_controller_address")),
    ]
    pairs += [(("read_control_configuration", field), ("read_control_configuration", "registered_baseline." + field))
              for field in ("kp", "ki", "kd")]
    pairs += [(("read_motion_test_conditions", "payload_record"), ("read_motion_test_conditions", "registered_baseline.payload_id")),
              (("read_motion_test_conditions", "equivalent_inertia"),
               ("read_motion_test_conditions", "registered_baseline.equivalent_inertia_kg_m2"))]
    display_ids = list(dict.fromkeys(report.fact_ids))
    for pair in pairs:
        ids = [fields[item] for item in pair if item in fields]
        if any(fid in display_ids for fid in ids):
            display_ids += [fid for fid in ids if fid not in display_ids]
    if len({facts[f]["snapshot_id"] for f in display_ids}) != 1:
        raise ValueError("Paired facts mix observations from different snapshots.")
    zh = report.language == "zh"
    headings = (translate('Facts (application-rendered)', 'zh'), translate('Interpretation (model inference)', 'zh'), translate('Unknowns / questions', 'zh'), translate('Next steps', 'zh')) if zh else (
        "Facts (application-rendered)", "Interpretation (model inference)", "Unknowns / questions", "Next steps")
    lines = [f"## {headings[0]}"]
    for fid in display_ids:
        fact = facts[fid]
        if fact["value"] is None:
            # No error code / no failed stage are valid nulls; missing observations are unknown.
            value = (translate('Unknown', 'zh') if zh else "Unknown") if fact["unavailable_reason"] else (translate('None', 'zh') if zh else "None")
            if fact["unavailable_reason"]:
                value += f" ({fact['unavailable_reason']})"
        else:
            value = json.dumps(fact["value"], ensure_ascii=False)
        lines.append(f"- {fact['labels'][0 if zh else 1]}{chr(0xff1a) if zh else ': '}{value} [{fact['evidence_id']}]")
    lines.append(f"\n## {headings[1]}")
    for claim in report.interpretations:
        refs = list(dict.fromkeys([facts[f]["evidence_id"] for f in claim.fact_ids] + claim.chunk_ids))
        lines.append("- " + claim.text + " " + "".join(f"[{ref}]" for ref in refs))
    lines.append(f"\n## {headings[2]}")
    lines += ["- " + q for q in report.questions] or ["- " + (translate('No additional questions.', 'zh') if zh else "No additional questions.")]
    lines.append(f"\n## {headings[3]}")
    lines += [f"{i}. {step}" for i, step in enumerate(report.next_steps, 1)]
    structured = report.model_dump()
    structured["rendered_fact_ids"] = display_ids
    return "\n".join(lines), structured
