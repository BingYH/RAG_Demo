# English speaking notes

The separate [Chinese translation](Chinese/speaker_notes.md) is available for rehearsal.

Use these as cues rather than reading every line. Follow the timings in
[Run of show](run_of_show.md). The main example is a synthetic PD investigation,
not a claim of physical robot validation or autonomous repair.

## 0:00 — Engineering question

I built this demo around a test-engineering question: when a joint response fails,
how do we turn the result into an evidence-based next step?

The example uses a simplified offline PD model with no integral term. The data
and acceptance limits are synthetic. My focus is the engineering process:
measurable requirements, reproducible evidence, structured investigation and
useful feedback to the responsible engineer.

## 0:40 — Evaluate the response

The target changes to 0.2 radians. The response overshoots and oscillates before
settling. Python calculates the metrics from the saved trajectory. Overshoot is
58.53 percent against a five-percent limit. Settling time is 2.56 seconds against
a 1.5-second limit.

The final-window error passes, but that does not make the test pass: transient
behavior matters too. I keep the numerical requirement decision deterministic
so the language model does not decide whether a measured value meets a threshold.
The conclusion applies to this joint, action and record.

## 1:35 — Investigate the configuration

Next, I compare the test configuration with the registered baseline. The record
shows Kd changing from 0.85 to 0.10. In this PD model, derivative feedback provides
velocity damping. The lower value is therefore a useful priority hypothesis
for the observed oscillation.

I would check why that setting changed and whether the test conditions are
comparable. I would not jump from a plausible explanation to a unique root cause.
In a real investigation, load, configuration and measurement conditions can
all affect interpretation. This report proposes verification; it does not tune
the controller or claim the issue is repaired.

## 2:40 — Show the supporting evidence

Here I can inspect the original configuration field and the relevant procedure.
They have different roles: the observation says what was recorded, while the
procedure explains the metric and the comparison rules.

The model selects fact IDs. The application renders the values and citations
from the returned fields, keeping registered and current values distinct. This
prevents some source-mapping mistakes. It does not prove every inference is
correct, so a separate review checks the explanation and questions.

## 3:35 — Handle missing information

This is a separate test with incomplete load records. The response still has
measurable deviations, but I cannot explain them by assuming the current payload
matches the registered baseline. The workflow pauses to ask what tool and load
were used and whether they changed.

This branch is determined from evidence before a model request. If the person
does not know, that is a valid answer. The original missing values remain missing;
the statement is stored as unverified context.

## 4:35 — Continue into useful support

I will now open a different, previously executed WSL ROS case to show the
continuation without waiting for another model run. Its report retains the
missing payload and inertia records. The draft carries the test identity,
checks, references, open issues and requested support.

An engineer can edit the text and review the complete draft. Creation requires
approval of that exact revision. Editing changes the hash and requires approval
again. Repeated approved creation returns the same local ticket rather than a
duplicate. I will leave this demonstration draft unapproved.

## 5:35 — Explain the engineering integration

The architecture deliberately gives each part a clear job. Python generates the
offline trajectory, calculates metrics and validates evidence. In ROS mode,
WSL publishes samples and a subscriber collects a complete capture. Windows
reads it through HTTP, checks identity and integrity, and recalculates metrics.
This is real ROS transport of synthetic data, not new sensor measurements.

RAG retrieves applicable procedures. Claude interprets the facts and suggests
investigation. LangGraph controls the branches, pauses, bounded retries and
approval. The Dashboard presents the result. This combines deterministic scripts,
cross-system interfaces and AI assistance in one inspectable workflow.

## 6:45 — Inspect execution

This is the historical trace for a prepared run. We can inspect generation,
validation and review, and see where the workflow paused. A review failure can
trigger one correction; repeated failure escalates instead of looping indefinitely.

LangSmith helps me investigate the application itself: which evidence reached
the model, which route ran, and what latency and token usage were recorded.
That is observable execution, not access to the model's internal reasoning.

## 7:45 — Engineering next step and contribution

My proposed next step is a controlled comparison: confirm the change intent,
check procedure and load conditions, obtain approval for the test configuration,
then capture a new run and compare the same metrics. The demo does not perform
that physical retest. A separate baseline curve is reference material, not proof
of repair.

What I want to demonstrate for this role is the connection between test software,
data analysis and technical support. I can turn a requirement into a check,
preserve the evidence, explain uncertainty and package a useful next action.
AI helps organize the investigation, while the calculations and engineering
approval remain explicit.

## Follow-up answers: outside the timed core

**Why PD rather than full PID?**

It isolates position feedback and damping in an understandable example. Ki is
zero, so integral windup is not a valid explanation here. I would extend the
model only for a defined test question.

**Why not just Python?**

Python is appropriate for calculations, integrity and thresholds. AI adds
language-based retrieval, explanation and handling of user context. The graph
coordinates the two, including clarification and human approval.

**Why LangGraph?**

The workflow has stateful branches and interruptions, not just one prompt.
Explicit nodes and checkpoints make pause/resume and bounded failure handling
inspectable. A simpler workflow might need less orchestration.

**Why ROS and HTTP?**

ROS demonstrates a Linux acquisition interface; HTTP provides a small read-only
boundary to Windows. The AI layer receives a frozen evidence contract, not an
unbounded topic stream. ROS is not a requirement asserted from this job posting.

**How would this connect to actual hardware?**

I would first establish the real acquisition interface, timestamps, units,
calibration, data integrity and approved procedures. I would replace the evidence
adapter without granting the model direct control. This demo alone does not
establish real-time performance, fieldbus integration or physical safety validation.

**What have you measured about quality?**

The repository has offline tests and limited live-model regression examples.
I can show those checks and their boundaries. I have not established a general
accuracy percentage, measured time saving or production reliability.

**How did you use AI while building the project?**

I used AI-assisted development and iterated on the engineering scope, evidence
interfaces and workflow behavior. I distinguish generated implementation from
verified behavior: I need to explain the design, inspect the data and test the
result. I would describe my own contribution and tool assistance openly rather
than claim every line was written manually.
