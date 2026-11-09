"""Bind observations to fields and render facts without model-written values."""

import copy
import json

from pydantic import BaseModel, ConfigDict, Field

# Labels belong to the application; values always come from the named tool field.
FIELDS = {
    "read_bench_inventory": {
        "registered_controller_address": ("登记的控制器地址", "Registered controller address"),
        "expected_client_version": ("登记的期望客户端版本", "Registered expected client version"),
        "expected_controller_version": ("登记的期望控制器版本", "Registered expected controller version"),
    },
    "read_runtime_config": {
        "client_version": ("本次运行的客户端版本", "Installed client version"),
        "supported_protocols": ("本次客户端支持的协议", "Client supported protocols"),
        "target_ip": ("本次加载的目标地址", "Loaded target address"),
        "config_revision": ("加载的配置版本", "Loaded configuration revision"),
        "workstation_address": ("工作站地址", "Workstation address"),
        "change_records": ("记录的配置或软件变更", "Recorded configuration or software changes"),
    },
    "read_connection_observations": {
        "link_up": ("本地网口链路状态", "Local link up"),
        "ping": ("配置端点的 ping 观察", "Configured endpoint ping observation"),
        "handshake_status": ("握手观察状态", "Observed handshake status"),
        "controller_version": ("握手取得的控制器版本", "Controller version observed during handshake"),
        "reported_protocol": ("握手取得的控制器协议", "Controller protocol observed during handshake"),
    },
    "read_initialization_status": {
        "last_completed_stage": ("最后完成的初始化阶段", "Last completed initialization stage"),
        "failed_stage": ("失败的初始化阶段", "Failed initialization stage"),
        "error_code": ("初始化错误码", "Initialization error code"),
        "external_interface_enabled": ("外部接口启用状态", "External interface enabled"),
        "state_stream.valid_records": ("观察窗口内有效状态记录数", "Valid state records in observation window"),
        "ros2_nodes": ("ROS 2 节点观察", "ROS 2 node observations"),
    },
}

FIELDS.update({
    "read_motion_test_conditions": {
        "test_id": ("本次运动测试编号", "Recorded motion test ID"),
        "joint_id": ("受测抽象关节", "Tested abstract joint"),
        "procedure_id": ("本次测试规程", "Recorded test procedure"),
        "execution_mode": ("运动测试执行方式", "Motion test execution mode"),
        "action": ("本次目标动作（rad、s）", "Recorded target action (rad, s)"),
        "observation_window_s": ("运动观察窗口（s）", "Motion observation window (s)"),
        "sample_period_s": ("轨迹采样周期（s）", "Trajectory sample period (s)"),
        "control_period_s": ("仿真控制周期（s）", "Simulation control period (s)"),
        "payload_record": ("本次负载与夹具记录", "Current payload and fixture record"),
        "equivalent_inertia": ("本次记录的等效惯量", "Recorded current equivalent inertia"),
        "test_context_status": ("本次测试条件完整性", "Recorded test context completeness"),
        "registered_baseline.payload_id": ("登记的基准负载", "Registered baseline payload"),
        "registered_baseline.equivalent_inertia_kg_m2": ("登记的基准等效惯量（kg·m²）", "Registered baseline inertia (kg*m^2)"),
    },
    "read_control_configuration": {
        "mode": ("本次控制模式", "Recorded control mode"),
        "kp": ("本次 Kp（N·m/rad）", "Recorded Kp (N*m/rad)"),
        "ki": ("本次 Ki（积分项未启用）", "Recorded Ki (integral disabled)"),
        "kd": ("本次 Kd（N·m·s/rad）", "Recorded Kd (N*m*s/rad)"),
        "torque_limit_nm": ("本次对称力矩限幅（N·m）", "Recorded symmetric torque limit (N*m)"),
        "config_revision": ("本次控制配置版本", "Recorded control configuration revision"),
        "change_records": ("记录的控制配置变更", "Recorded control configuration changes"),
        "registered_baseline.kp": ("登记的基准 Kp", "Registered baseline Kp"),
        "registered_baseline.ki": ("登记的基准 Ki", "Registered baseline Ki"),
        "registered_baseline.kd": ("登记的基准 Kd", "Registered baseline Kd"),
    },
    "read_motion_test_results": {
        "metrics_version": ("运动指标计算版本", "Motion metrics calculation version"),
        "model_version": ("离线仿真模型版本", "Offline simulation model version"),
        "trajectory_id": ("计算所用轨迹编号", "Input trajectory ID"),
        "trajectory_sha256": ("计算所用轨迹 SHA256", "Input trajectory SHA256"),
        "sample_count": ("已校验轨迹采样数", "Verified trajectory sample count"),
        "data_integrity": ("轨迹记录完整性", "Trajectory completeness"),
        "response_requirement_status": ("本次响应的演示要求结果", "Response demo requirement result"),
        "metrics.overshoot_pct": ("超调指标与演示要求比较", "Overshoot metric and demo requirement comparison"),
        "metrics.settling_time_s": ("调节时间指标与演示要求比较", "Settling-time metric and demo requirement comparison"),
        "metrics.steady_state_error_rad": ("末段平均误差与演示要求比较", "Final-window mean error and demo requirement comparison"),
        "metrics.peak_abs_error_rad": ("峰值绝对误差（描述性）", "Peak absolute error (informational)"),
        "metrics.saturation_fraction": ("采样输出限幅占比（描述性）", "Sampled output saturation fraction (informational)"),
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
    headings = ("事实（程序生成）", "解读（模型推断）", "未知与待确认", "下一步建议") if zh else (
        "Facts (application-rendered)", "Interpretation (model inference)", "Unknowns / questions", "Next steps")
    lines = [f"## {headings[0]}"]
    for fid in display_ids:
        fact = facts[fid]
        if fact["value"] is None:
            # No error code / no failed stage are valid nulls; missing observations are unknown.
            value = ("未知" if zh else "Unknown") if fact["unavailable_reason"] else ("无" if zh else "None")
            if fact["unavailable_reason"]:
                value += f" ({fact['unavailable_reason']})"
        else:
            value = json.dumps(fact["value"], ensure_ascii=False)
        lines.append(f"- {fact['labels'][0 if zh else 1]}：{value} [{fact['evidence_id']}]")
    lines.append(f"\n## {headings[1]}")
    for claim in report.interpretations:
        refs = list(dict.fromkeys([facts[f]["evidence_id"] for f in claim.fact_ids] + claim.chunk_ids))
        lines.append("- " + claim.text + " " + "".join(f"[{ref}]" for ref in refs))
    lines.append(f"\n## {headings[2]}")
    lines += ["- " + q for q in report.questions] or ["- " + ("未提出额外问题。" if zh else "No additional questions.")]
    lines.append(f"\n## {headings[3]}")
    lines += [f"{i}. {step}" for i, step in enumerate(report.next_steps, 1)]
    structured = report.model_dump()
    structured["rendered_fact_ids"] = display_ids
    return "\n".join(lines), structured
