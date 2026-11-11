# Dashboard: local operation and bilingual presentations

The entry point is `streamlit_app.py`, reusing LangGraph and
`data/checkpoints/diagnosis.sqlite3`. Paste a current-version CLI Thread ID to
open it. Refreshing, viewing curves and switching languages do not call the model.

## Start

Run from the project root in ordinary PowerShell:

~~~powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
~~~

Open `http://127.0.0.1:8501`. The service is local, not publicly deployed.
Its process needs outbound access to Claude and LangSmith; do not start it in
a sandbox that blocks that access. The earlier APIConnectionError was traced
to process network restrictions, not exhausted credits. Keys come from existing
local environment variables and are neither displayed nor saved by the page.

After changing Python modules/interfaces under `rag_demo/`, press Ctrl+C in the
server terminal, restart with the command above, then refresh. A browser refresh
alone may mix updated page code with cached backend interfaces. The earlier
`output_language`/error-handler mismatch was resolved by a full restart.
Restarting does not erase SQLite threads or tickets.

## Data source: Local JSON / WSL ROS

The sidebar offers:

- Local JSON: three initialization and three motion fixtures; no WSL service needed.
- WSL ROS: joint-response replay only. The bridge selects the actual scenario;
  the page shows the received curve, test/capture IDs and metrics rather than
  choosing a local scenario.

Start the bridge in another PowerShell at the project root and leave it running
without `--verify-only`:

~~~powershell
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_load_unknown
~~~

Select WSL ROS, confirm the port (default 8765), and click **Check and load ROS
capture**. This requests and validates evidence only; it does not call the model.
Diagnosis becomes available after a successful load. Inspect the curve, then
start diagnosis. If the capture changes between loading and starting, identity
verification rejects it rather than silently binding new data.

The case header identifies the actual source. Language, source and scenario
selection affect new threads only; paused cases keep their source. Unavailable,
incomplete or invalid ROS captures fail explicitly before model construction,
with no Local JSON fallback.

New ROS threads save `data_source=wsl_ros` and capture/hash `source_metadata`.
The full trajectory and snapshot are cached at
`data/ros_captures/<capture_id>.json`. Refresh, clarification and approval use the
original checkpoint and validated cache without reconnecting to ROS. Curves and
reports remain viewable after the bridge stops. Missing/tampered caches produce
an explicit validation warning instead of a substitute curve. Trajectories are
excluded from model context and graph state to avoid copying full CSV data at
each node.

Trace metadata and tickets retain the source. It is offline synthetic replay
transported through ROS, not new physical measurements or a rerun controller.
See [ROS bridge](ros_replay_bridge.md). Restart Streamlit after backend changes.

## Language and suggested presentation

The sidebar Language selector offers English and Chinese. English is the default.
English covers scenarios, metrics, buttons, statuses, clarification, fact labels,
draft previews and errors. New threads persist their requested output language;
a mismatched model report enters the existing correction/escalation path.
New English tickets also have English default titles and support requests.
Downloaded JSON remains linked to original facts.

For an English interview presentation, start a new English thread:

1. Select oscillation, inspect the curve/requirements, then diagnose.
2. Explain facts versus inference in Diagnosis and inspect Evidence & knowledge.
3. Use missing-load data to show clarification; an unknown reply retains the gap.
4. Review the complete Support ticket, edit and reapprove, or cancel.
5. Inspect node history, usage and verified traces in Execution.

Language switching changes presentation text only. Stored reports, human
questions/notes, evidence and drafts retain their original content. A saved
Chinese report stays Chinese in an English UI with a notice; start a new English
thread for English diagnosis. Resuming uses the original output language.
Switching does not change draft hashes or invalidate/fabricate approval.

Raw evidence/draft JSON retains technical identifiers, source references and
bilingual fact labels in its original structure. It is not a newly translated
data copy. Matplotlib plots already use English.

## Layout and validation

Top padding increased from 2rem to 5rem (4.5rem on narrow screens) to clear the
fixed Streamlit toolbar and reveal BENCH AI / ENGINEERING SUPPORT DEMO.

The pre-migration baseline had 86 passing tests. UI coverage includes both
sources, load-before-start, unchanged existing sources after selector changes,
offline clarification resume, no curve substitution on cache tampering, no model
construction for unavailable sources, CLI thread loading, ticket edit/approval/
deduplication and language switching. Ticket tests use temporary directories;
they do not approve the user's current ticket.

Live English validation on 2026-11-08, thread `ui-english-bf8314a877`:

- English load clarification paused before model use;
  [16-step trace read-back](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/d15827ba-42d0-4857-b1a9-8e4b7f58930b/run/d15827ba-42d0-4857-b1a9-8e4b7f58930b).
- An explicit demo-validation reply resumed an `en` report, passed evidence
  review and produced BENCH-001 support request with a readable English draft;
  [15-step trace read-back](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/3b65259e-9b29-4ab9-a2ce-0ca480ecbd60/run/3b65259e-9b29-4ab9-a2ce-0ca480ecbd60).
  It stopped at approval; no ticket was automatically created.

Current limits: model-node connection failures require a new UI thread; approved
local creation can retry idempotently. Unverified trace upload/read-back does
not automatically rerun the model. ROS replay is synthetic; there is no physical
device control, external support integration or public deployment.

On 2026-11-09, the live UI path also passed: WSL missing-load replay → load 601
samples → English diagnosis → pre-model clarification → explicit demo reply →
English report/draft awaiting approval. Thread
`38a1c7d28c0644fcbf849b1a9f9cbaf0` retained `wsl_ros` and the same capture in
the draft. Both traces passed read-back:
[clarification, 16 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e53789ae-6c8b-4424-b770-fec0105fa6da/run/e53789ae-6c8b-4424-b770-fec0105fa6da),
[resume to approval, 15 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/607bb271-ed44-4474-9e38-4fbd88a503f0/run/607bb271-ed44-4474-9e38-4fbd88a503f0).
No automatic approval occurred. Review can still miss repeated questions or
wording problems; finite validation is not proof of semantic correctness.
