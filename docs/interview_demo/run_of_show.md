# Run of show: finish by 9:15

## Before the meeting

Run commands from the RAG_Demo root. Prepare in English unless the audience asks
for Chinese. Installation, compilation and package downloads happen beforehand.

```powershell
# Terminal A: local Dashboard
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py

# Terminal B: optional live ROS evidence preview; keep it running
.\.venv\Scripts\python.exe scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation

# Terminal C: validate fixtures and find usable existing English presentation cases
.\.venv\Scripts\python.exe scripts/prepare_interview_demo.py
```

The preparation script uses local files/checkpoints only. It makes no model/HTTP
request, changes no workflow, and approves nothing. Its local inventory is written
to `data/presentation/session_inventory.json`. Copy the listed Thread IDs into
the Dashboard's **Open an existing thread** field and click **Open thread**.
Do not use historical run JSON as a new checkpoint or try to rewind a resumed thread.

Prepare these browser tabs before the meeting:

| Tab | Content | Mode/source |
| --- | --- | --- |
| 1 | engineering_workflow.svg | Presentation diagram |
| 2 | Dashboard: English oscillation report | Verified historical Local JSON case |
| 3 | Dashboard: scenario preview, Local JSON, Missing load context | Fresh clarification demonstration; no report generation needed |
| 4 | Dashboard: English missing-load report/draft | Verified historical WSL ROS case, original frozen capture |
| 5 | system_architecture.svg | Presentation diagram |
| 6 | LangSmith trace for one prepared report | Historical trace, workspace access required |

If independent Dashboard tabs share unexpected state, open the required case
through its Thread ID rather than relying on tab contents. Keep the inventory
available. Browser zoom should make the two headline metrics and the report
readable; collapse long JSON/details panels. Test scrolling and tab changes.

Check saved ROS curves load from the validated local cache. Do not substitute a
JSON curve when a saved ROS capture fails validation. If a required case is
missing, prepare it explicitly before rehearsal through the UI and rerun inventory;
this preparation script does not silently create paid model runs.

For a live ROS preview: select **WSL ROS**, then **Check and load ROS capture**.
Confirm 601 samples, the capture/test identity and source. Loading is not model
diagnosis. Capture success and response failure can both be true. Use the local
JSON/historical default sequence if the bridge is unavailable, saying so explicitly.

## Timed presentation

| Time | Screen and action | Engineering message | Exit condition |
| --- | --- | --- | --- |
| 0:00–0:40 | Tab 1: show investigation diagram; introduce the problem | A failed response needs requirements, evidence and a verified next step | State PD, Ki=0 and synthetic scope once |
| 0:40–1:35 | Tab 2: curve/metrics; optionally preview baseline briefly | Target is 0.2 rad; 58.53% overshoot exceeds 5%, 2.56 s exceeds 1.5 s | Explain why final error passing does not rescue the transient |
| 1:35–2:40 | Diagnosis and Facts and sources; point to current/baseline Kd | Kd 0.85 → 0.10 supports reduced damping as a hypothesis | Say what you would verify, without declaring a unique cause |
| 2:40–3:35 | Evidence & knowledge; show one field and one passage | Measurements/configuration establish observations; procedure supplies definitions | Show source binding, not every JSON field |
| 3:35–4:35 | Tab 3: select Missing load context; Start new diagnosis; show pause | Missing current payload/inertia cannot be filled from registry | Explain that this is a separate test; no model call occurs before this pause |
| 4:35–5:35 | Tab 4: disclose saved resumed WSL ROS case; show retained gap and draft | Unknown replies remain unverified context; support can proceed with gaps | Inspect draft and approval control; leave it unapproved |
| 5:35–6:45 | Tab 5: architecture | Python computes/validates; ROS transports; AI interprets; graph coordinates | Explain these responsibilities in one pass |
| 6:45–7:45 | Tab 6: expand three relevant trace nodes | Execution/review/citations are observable; this is not internal model thought | Point out generation, validation/review and approval pause |
| 7:45–9:15 | Return to report/diagram; describe proposed retest and your contribution | Verify change intent and comparable conditions, approve a test plan, repeat and compare | Finish with the value to the engineering team |
| 9:15–10:00 | Reserve | Allow slow navigation or a short question | Do not start another scenario |

Keep the main screen on the curve/report for most of the talk. The missing-load
branch is a one-minute contrast, not a second full presentation. Technical source
details and initialization failures are follow-up material.

## Exact question and clarification wording

Optional live oscillation question:

> Analyze this offline single-joint PD response. Identify failed demo requirements,
> compare current and registered control settings, distinguish observations from
> hypotheses, and propose engineering verification. Reply in English.

For the fresh missing-load case, stop at the displayed clarification in the timed
default route. Explain the following example reply without submitting it:

> Demo statement: I do not know whether the tool or payload changed. Please retain
> the missing load and inertia records as unresolved evidence.

Then open the existing resumed WSL case and say it is a **different, previously
executed run** showing the continuation. It must not be presented as the continuation
of the fresh Local JSON thread. Resume the fresh thread only if time permits;
doing so can incur model calls and consumes that thread's interrupt.

## Optional live generation

If rehearsed and requested, start one fresh English oscillation diagnosis, then
explain the architecture while it runs. After 30 seconds of visible waiting,
open the prepared report and state that it is a historical run. API latency and
bounded corrections can exceed this budget. Do not call a pending run complete.
An interrupted/failed model request is not a credit-balance diagnosis.

## Proposed retest, not a claimed repair

1. Check the Kd change record and whether the change was intended.
2. Check recorded procedure, payload/inertia, sampling and configuration scope.
3. Have the responsible engineer approve a comparable test plan/configuration.
4. Capture a new test/snapshot ID and recompute the same metrics.
5. Compare with requirements and baseline, retain evidence and report remaining deviations.

No automated tuning or physical retest occurs in this demo. Do not show the
separate baseline fixture as proof that the fault was repaired.

## Failure and time shortcuts

- At 3:35, if behind: show the missing-load pause but omit its report details.
- At 6:45, if behind: skip the trace UI and point to observability in the diagram.
- If LangSmith access fails: show local node history/review records, explicitly local.
- If model/network service fails: use saved reports and validated cached evidence.
- If ROS fails: disclose the source and use the historical/source-labeled route;
  the application itself never silently falls back.
- If a draft is already approved: do not use it to demonstrate pending approval.
  Select a separate pending draft. Do not approve an existing user ticket for rehearsal.

## Rehearsal record

Target speaking notes are approximately 800–950 words. At a deliberate technical
pace, leave the remainder for clicks and pointing. Time the complete screen
sequence twice; do not infer timing from word count alone.

Record actual total time, longest transition, fallback used and any question that
needs a clearer answer. Aim for <=9:15 before the interview. No timed rehearsal
or new live-model run is claimed by these preparation materials.
