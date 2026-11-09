"""Deterministic offline PD plant and metrics; no model or hardware access."""

import csv
import hashlib
import io
import math
from pathlib import Path

MODEL_VERSION = "joint-inertia-pd-v1"
METRICS_VERSION = "joint-step-metrics-v1"
SCENARIOS = ("joint_tracking_baseline", "joint_tracking_oscillation", "joint_tracking_load_unknown")
ROOT = Path(__file__).resolve().parent / "motion_scenarios"
COLUMNS = ("time_s", "target_position_rad", "actual_position_rad", "velocity_rad_s",
           "requested_torque_nm", "applied_torque_nm")


def simulate(*, inertia: float, kd: float) -> list[dict]:
    if not math.isfinite(inertia) or inertia <= 0 or not math.isfinite(kd) or kd < 0:
        raise ValueError("Invalid plant or controller parameters.")
    q = velocity = 0.0
    rows = []
    for step in range(6001):
        target = 0.0 if step < 500 else 0.2
        requested = 4.0 * (target - q) - kd * velocity
        applied = max(-2.0, min(2.0, requested))
        if step % 10 == 0:
            rows.append(dict(zip(COLUMNS, (step / 1000, target, q, velocity, requested, applied))))
        velocity += (applied - 0.05 * velocity) / inertia * 0.001
        q += velocity * 0.001
    return rows


def csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def load_trajectory(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError("Trajectory columns do not match the motion schema.")
        return [{key: float(value) for key, value in row.items()} for row in reader]


def calculate_metrics(rows: list[dict]) -> dict:
    """Evaluate saved 100 Hz step samples, rejecting corrupt or irregular data."""
    if not rows:
        raise ValueError("Empty trajectory.")
    for i, row in enumerate(rows):
        if set(row) != set(COLUMNS) or not all(math.isfinite(v) for v in row.values()):
            raise ValueError("Missing or non-finite trajectory data.")
        if abs(row["time_s"] - i * 0.01) > 1e-9:
            raise ValueError("Trajectory sample grid is invalid.")
        expected = 0.0 if i < 50 else 0.2
        if row["target_position_rad"] != expected:
            raise ValueError("Trajectory does not match the fixed step procedure.")
        if (abs(row["applied_torque_nm"]) > 2.0 + 1e-12 or
                abs(row["applied_torque_nm"] - max(-2., min(2., row["requested_torque_nm"]))) > 1e-12):
            raise ValueError("Trajectory torque limit is inconsistent.")
    if len(rows) > 601:
        raise ValueError("Trajectory exceeds the fixed procedure window.")
    complete = len(rows) == 601
    post = rows[50:]
    values = {name: None for name in ("overshoot_pct", "settling_time_s", "steady_state_error_rad",
                                     "peak_abs_error_rad", "saturation_fraction")}
    settling_reason = "insufficient_observation_window"
    if post:
        values["overshoot_pct"] = 100 * max(0., max(r["actual_position_rad"] for r in post) - .2) / .2
        values["peak_abs_error_rad"] = max(abs(.2 - r["actual_position_rad"]) for r in post)
        values["saturation_fraction"] = sum(abs(r["requested_torque_nm"]) > 2. for r in post) / len(post)
    if complete:
        tail = rows[550:]
        values["steady_state_error_rad"] = sum(.2 - r["actual_position_rad"] for r in tail) / len(tail)
        last_bad = max((i for i, r in enumerate(post) if abs(r["actual_position_rad"] - .2) > .004), default=-1)
        candidate = last_bad + 1
        if candidate < len(post) and post[-1]["time_s"] - post[candidate]["time_s"] >= .5 - 1e-9:
            values["settling_time_s"] = round(post[candidate]["time_s"] - .5, 10)
            settling_reason = None
        else:
            settling_reason = "not_settled_within_observation_window"
    specs = (("overshoot_pct", "%", 5., "le", "DEMO-RESP-01"),
             ("settling_time_s", "s", 1.5, "le", "DEMO-RESP-02"),
             ("steady_state_error_rad", "rad", .002, "abs_le", "DEMO-RESP-03"),
             ("peak_abs_error_rad", "rad", None, None, None),
             ("saturation_fraction", "fraction", None, None, None))
    metrics = []
    for name, unit, threshold, operator, requirement in specs:
        value = values[name]
        if not complete:
            status, reason = "not_evaluable", "insufficient_observation_window"
        elif requirement is None:
            status, reason = "informational", None
        elif value is None:
            status, reason = "fail", settling_reason
        else:
            compared = abs(value) if operator == "abs_le" else value
            status, reason = ("pass" if compared <= threshold else "fail"), None
        metrics.append({"metric_id": name, "value": value, "unit": unit,
                        "requirement_id": requirement, "threshold": threshold, "operator": operator,
                        "result": status, "reason": reason,
                        "window_s": [5.5, 6.] if name == "steady_state_error_rad" else [.5, rows[-1]["time_s"]]})
    return {"metrics_version": METRICS_VERSION, "sample_count": len(rows),
            "data_integrity": "complete" if complete else "incomplete",
            "response_requirement_status": "not_evaluable" if not complete else
                ("fail" if any(m["result"] == "fail" for m in metrics) else "pass"),
            "metrics": metrics}


def trajectory_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_fixture(directory: Path) -> tuple[dict, list[dict]]:
    import json
    state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
    path = directory / "trajectory.csv"
    rows = load_trajectory(path)
    results = state["observations"]["read_motion_test_results"]["data"]
    if results["trajectory_sha256"] != trajectory_hash(path):
        raise ValueError("Trajectory hash mismatch.")
    computed = calculate_metrics(rows)
    if any(results[key] != value for key, value in computed.items()):
        raise ValueError("Saved metrics disagree with trajectory.")
    return state, rows


def plot_response(state: dict, rows: list[dict], output: Path) -> None:
    import os
    cache = Path(__file__).resolve().parents[1] / "data" / "matplotlib"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    results = state["observations"]["read_motion_test_results"]["data"]
    metrics = {m["metric_id"]: m for m in results["metrics"]}
    fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
    times = [r["time_s"] for r in rows]
    ax.plot(times, [r["target_position_rad"] for r in rows], "--", color="#58677c", label="Target position", linewidth=2)
    ax.plot(times, [r["actual_position_rad"] for r in rows], color="#176bba", label="Actual position", linewidth=2)
    ax.fill_between([.5, 6.], .196, .204, color="#23a574", alpha=.18, label="2% settling band")
    ax.axvline(.5, color="#8896a8", linewidth=1)
    peak = max(rows[50:], key=lambda r: r["actual_position_rad"])
    overshoot = metrics["overshoot_pct"]["value"]
    if overshoot > .01:
        ax.annotate(f"Peak: {peak['actual_position_rad']:.3f} rad", xy=(peak["time_s"], peak["actual_position_rad"]),
                    xytext=(peak["time_s"] + .6, peak["actual_position_rad"]),
                    arrowprops={"arrowstyle": "->", "color": "#475569"})
    settle = metrics["settling_time_s"]["value"]
    label = f"{settle:.2f} s" if settle is not None else "not observed"
    if settle is not None:
        ax.axvline(.5 + settle, color="#23a574", linestyle=":", linewidth=1.4,
                   label=f"Settling time: {label} after step")
    context = state["observations"]["read_motion_test_conditions"]["data"]["test_context_status"]
    display_id = state["test_id"] if len(state["test_id"]) <= 24 else state["test_id"][:15] + "..."
    ax.set_title(f"{display_id} | Offline synthetic single-joint PD response\n"
                 f"Overshoot: {overshoot:.1f}% (limit 5%)   Settling: {label} (limit 1.5 s)\n"
                 f"Response: {results['response_requirement_status'].upper()}   Test context: {context}", fontsize=11)
    ax.set(xlabel="Time (s) | step starts at 0.5 s", ylabel="Position (rad)",
           xlim=(0, 6), ylim=(-.015, .345))
    ax.grid(alpha=.2)
    ax.legend(loc="lower right")
    fig.supxlabel("Demo requirements only. One joint and one test action; no hardware or whole-robot validation.", fontsize=9)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)
