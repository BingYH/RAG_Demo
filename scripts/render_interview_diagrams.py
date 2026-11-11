"""Render standalone presentation diagrams using local Matplotlib only."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUTPUT = Path(__file__).resolve().parents[1] / "docs/interview_demo"
INK, MUTED, TEAL, BLUE, AMBER = "#14283f", "#53657a", "#087f8c", "#3268a8", "#a96a16"


def canvas(title, subtitle):
    figure, axis = plt.subplots(figsize=(16, 9), dpi=130)
    figure.patch.set_facecolor("#f4f7fb")
    axis.set(xlim=(0, 1600), ylim=(900, 0))
    axis.axis("off")
    axis.text(45, 62, title, fontsize=23, fontweight="bold", color=INK)
    axis.text(45, 101, subtitle, fontsize=11, color=MUTED)
    figure.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.02)
    return figure, axis


def box(axis, x, y, title, body, color=TEAL, width=315, height=116):
    axis.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0,rounding_size=12",
                                linewidth=1.2, edgecolor=color, facecolor="white"))
    axis.text(x+17, y+29, title, fontsize=12, color=color, fontweight="bold")
    axis.text(x+17, y+57, body, fontsize=10.5, color=INK, va="top", linespacing=1.55)


def arrow(axis, start, end, label="", dashed=False, bend=0):
    axis.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14,
        linewidth=1.5, color=MUTED, linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={bend}"))
    if label:
        axis.text((start[0]+end[0])/2, (start[1]+end[1])/2-12, label,
                  fontsize=9, color=MUTED, ha="center", bbox=dict(facecolor="#f4f7fb", edgecolor="none", pad=2))


def save(figure, name):
    for suffix in ("svg", "png"):
        figure.savefig(OUTPUT / f"{name}.{suffix}", facecolor=figure.get_facecolor())
    plt.close(figure)


def engineering():
    figure, ax = canvas("From failed response to an engineering next step",
        "Main case: offline single-joint PD, Ki = 0. Synthetic data and project-defined limits.")
    xs = [45, 440, 835, 1230]
    width = 285
    top = [
        ("1  Define requirements", "Overshoot <= 5%\nSettling time <= 1.5 s"),
        ("2  Bind the evidence", "Procedure, test ID, trajectory\nConfiguration and load context"),
        ("3  Compute in Python", "58.53% overshoot: fail\n2.56 s settling: fail"),
        ("4  Compare configuration", "Recorded Kd: 0.85 -> 0.10\nCheck change intent and scope"),
    ]
    for x, (title, body) in zip(xs, top):
        box(ax, x, 170, title, body, width=width)
    for left, right in zip(xs, xs[1:]): arrow(ax, (left+width, 228), (right, 228))
    box(ax, xs[3], 385, "5  Check context", "Complete conditions?\nMissing values stay unknown.", width=width)
    box(ax, xs[2], 385, "6  Clarify if missing", "Separate missing-load test\nReply is unverified context.", AMBER, width=width)
    box(ax, xs[1], 385, "7  Explain with evidence", "RAG + Claude: hypotheses\nNo unique-cause assumption", BLUE, width=width)
    box(ax, xs[0], 385, "8  Validate and review", "Bind facts and references\nCorrect once or escalate", BLUE, width=width)
    arrow(ax, (xs[3]+width/2, 286), (xs[3]+width/2, 385))
    arrow(ax, (xs[3], 443), (xs[2]+width, 443), "Missing")
    arrow(ax, (xs[2], 443), (xs[1]+width, 443))
    ax.plot([xs[3]+90, xs[3]+90, xs[1]+width/2], [385, 340, 340], color=MUTED, linewidth=1.5)
    arrow(ax, (xs[1]+width/2, 340), (xs[1]+width/2, 385))
    ax.text(965, 329, "Complete: continue", fontsize=9, color=MUTED, ha="center")
    arrow(ax, (xs[1], 443), (xs[0]+width, 443))
    box(ax, xs[0], 620, "9  Review support draft", "Facts, gaps and next checks\nEngineer edits / approves / cancels", width=width)
    box(ax, xs[1], 620, "10  Create local ticket", "Approve exact revision/hash\nIdempotent local record", width=width)
    box(ax, xs[2], 620, "Proposed retest", "Approve a comparable retest\nNew capture; same requirements", AMBER, width=width)
    arrow(ax, (xs[0]+width/2, 501), (xs[0]+width/2, 620))
    arrow(ax, (xs[0]+width, 678), (xs[1], 678), "Approved")
    arrow(ax, (xs[1]+width, 678), (xs[2], 678), dashed=True)
    ax.text(xs[3], 653, "Retest is proposed.\nNo automatic tuning,\nmovement or repair.", fontsize=12, color=AMBER, linespacing=1.7)
    ax.text(45, 824, "Engineering judgement: a failed metric is an observation; a plausible cause is a hypothesis; a retest needs its own evidence.", fontsize=12, color=INK)
    save(figure, "engineering_workflow")


def architecture():
    figure, ax = canvas("Deterministic scripts + observable AI workflow",
        "Two explicit evidence sources. A frozen evidence contract connects acquisition, analysis and technical support.")
    columns = [(45, "EVIDENCE SOURCES", TEAL), (440, "WINDOWS / PYTHON", TEAL),
               (835, "AI WORKFLOW", BLUE), (1230, "ENGINEER / OUTPUT", AMBER)]
    for x, label, color in columns:
        ax.text(x, 149, label, fontsize=11, fontweight="bold", color=color)
    width = 285
    box(ax, 45, 180, "Local JSON / CSV", "Versioned synthetic fixtures\nOffline, reproducible evidence", width=width)
    box(ax, 45, 385, "WSL ROS 2 replay", "Publisher -> subscriber\n601 samples -> frozen capture", width=width)
    box(ax, 440, 180, "Read-only adapters", "Explicit source selection\nROS: localhost HTTP /snapshot", width=width)
    box(ax, 440, 385, "Validate and calculate", "Identity, sequence and hash\nRecompute metrics; bind facts", width=width)
    box(ax, 835, 180, "LangGraph + SQLite", "State, routes and pause/resume\nBounded retries and approval", BLUE, width=width)
    box(ax, 835, 385, "RAG + Claude", "Retrieve applicable guidance\nStructured interpretation", BLUE, width=width)
    box(ax, 1230, 180, "Streamlit Dashboard", "Curve, facts and sources\nEnglish / Chinese presentation", AMBER, width=width)
    box(ax, 1230, 385, "Human confirmation", "Edit / approve / cancel draft\nExact revision and content hash", AMBER, width=width)
    arrow(ax, (330, 238), (440, 238))
    arrow(ax, (330, 443), (440, 238), "HTTP")
    arrow(ax, (582, 296), (582, 385))
    arrow(ax, (725, 443), (835, 238), "Frozen facts")
    arrow(ax, (977, 296), (977, 385), "Orchestrates")
    arrow(ax, (1120, 238), (1230, 238))
    arrow(ax, (1372, 296), (1372, 385))
    box(ax, 440, 635, "LangSmith", "Node / model / tool traces\nUsage, latency and review results", BLUE, width=width)
    box(ax, 835, 635, "Validation + review", "Application source checks\nModel review; one correction", BLUE, width=width)
    box(ax, 1230, 635, "Local ticket store", "SQLite + recoverable JSON\nIdempotent approved creation", AMBER, width=width)
    arrow(ax, (977, 501), (977, 635))
    ax.plot([1120, 1165, 1165, 1005], [693, 693, 330, 330], color=MUTED, linewidth=1.5)
    arrow(ax, (1005, 330), (1005, 296))
    ax.text(1153, 549, "Pass / correction", fontsize=9, rotation=90, color=MUTED, va="center")
    arrow(ax, (835, 693), (725, 693), "Execution traces", dashed=True)
    arrow(ax, (1372, 501), (1372, 635), "Approved only")
    ax.text(45, 635, "Python owns numeric checks.\nAI assists interpretation.\nThe graph owns control flow.\nPeople approve business actions.", fontsize=12, color=INK, linespacing=1.9)
    ax.text(45, 838, "ROS transports synthetic replay, not physical measurements. The AI has no motion or controller-parameter write interface.", fontsize=12, color=INK)
    save(figure, "system_architecture")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    engineering()
    architecture()
    print("DIAGRAMS_READY: docs/interview_demo (SVG and PNG)")
