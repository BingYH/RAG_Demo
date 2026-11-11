# CLI diagnosis prototype validation record

Initial validation: 2026-11-07, model claude-haiku-5-5, knowledge version
37fe4f15f961fd0a, five documents/25 chunks, local ONNX MiniLM + Chroma.
This is a development record, not a full evaluation set or accuracy promise.
Sections record successive historical milestones; later sections supersede
earlier implementation limitations.

## Live-model checks

| Scenario | Observed after reading the answer | Trace |
| --- | --- | --- |
| Connection timeout | Distinguished registry .11 from configuration .12; remote versions stayed unknown; requested address checks without declaring damaged hardware or a successful repair | [12 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/df168f29-e4c9-4e0f-91d1-25524787fdc9/run/df168f29-e4c9-4e0f-91d1-25524787fdc9) |
| Version mismatch | Compared observed protocol 1 with client [2], identified handshake incompatibility without upgrade/rollback | [11 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/9120bcd8-0c3d-4e34-9f3d-a65547b9b72e/run/9120bcd8-0c3d-4e34-9f3d-a65547b9b72e) |
| Healthy | Confirmed diagnostic_ready, noted uncollected ROS nodes and no motion/safety/full-functional acceptance | [12 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/d6d56212-d166-40b2-b44e-46c5090cbaec/run/d6d56212-d166-40b2-b44e-46c5090cbaec) |

v2 API read-back confirmed completed model, tool, retrieval and outer records.
Links require workspace access and remain subject to retention. Local outputs/
usage reside in ignored data/runs/.

## Issues found and corrected

- Truncated initial answers: increased output budget and requested concision.
  Truncation fails explicitly rather than becoming a completed diagnosis.
- Shortened log evidence IDs: documented full suffixes, validated IDs and added
  one bounded correction; repeated invalid output fails.
- New /trace/.../run/... URL format: fixed project ID extraction and read the
  original trace again without another model request.
- A mismatch answer used English: the historical prompt then made Simplified
  Chinese/headings explicit. The current English-default policy supersedes that
  preference; model phrasing remains uncertain.

## Offline checks and initial limits

Tests covered tool parameters, session isolation, document scope, calls and
citation boundaries; all three fixtures were checked. Actual vector queries
retrieved address, compatibility and diagnostic_ready boundary guidance.

Valid IDs do not prove support for every statement; human/evaluator review is
still needed. At this initial milestone there was no automated semantic scoring,
multi-turn dialogue, graph recovery or ticket creation. Fixed evaluations and
orchestration were the next steps.

## Stage 2: fact-to-source binding

On the same day, diagnosis-v2-bound-facts added a field-fact registry and Pydantic
reports. submit_analysis selects fact IDs; code renders names, values and
citations. Registered/current versions and addresses appear together; models
cannot submit fact values/evidence IDs. Paths, origins, snapshots and times
are retained locally and in tool traces.

Tests covered expected 1.4.0 versus installed 2.0.0, equal values with different
sources, registered-but-unobserved controller versions, fabricated bindings,
unreturned chunks and mixed snapshots. Facts render deterministically; inference
semantics are not guaranteed.

Live rechecks:

- [Timeout, 12 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/405a6ad3-3b33-4736-8273-d7c52f08f8a8/run/405a6ad3-3b33-4736-8273-d7c52f08f8a8): runtime, registry and connection facts retained separate sources.
- [Mismatch, 12 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e20d65c0-abdd-430b-9683-fd2f8ce12f02/run/e20d65c0-abdd-430b-9683-fd2f8ce12f02): actual client 2.0.0 cited EV-026-02; expected 1.4.0 cited EV-026-01.

The first recheck exceeded the original fact capacity and received vague
correction feedback. Capacity was expanded, concise selection requested,
field-specific errors returned and output budget increased; truncation still fails.

Human inspection still found 09:50 restated as 10:50 in interpretation, while
the program-rendered record retained 09:50. Field binding fixes source mismatch
in facts, not every numeric/time restatement in model prose. Evaluation should
cover these separately.

## Stage 3: evidence review of interpretation and questions

diagnosis-v3-evidence-review added a separate evidence_review request after
structural checks. It compares report, facts and cited chunks for network
overclaims, redundant questions, incompatible options and direct contradictions.
Structural, citation and semantic issues share one correction. Usage includes
generation/review; the reviewer performs no business action.

- [Complete mismatch validation, 13 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/de82a51d-8cc0-4ec0-8cdd-30087036f009/run/de82a51d-8cc0-4ec0-8cdd-30087036f009):
  no repeated controller-version question, bounded ping/handshake conclusions,
  evaluation of the documented 1.4.0/protocol 1 baseline and verification of
  protocol 2 evidence if retaining 2.0.0.
- [Fixed regression](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/4b9556d8-12c0-4b7b-8ee5-fd069660f315/run/4b9556d8-12c0-4b7b-8ee5-fd069660f315):
  bad variant flagged network_overclaim, redundant_question and
  compatibility_error; bounded variant passed.

The first regression missed protocol-1-or-2 ambiguity inside a question. Explicit
question-level protocol constraints made both variants pass their expectations.
One positive/negative pair cannot guarantee other wordings or all citations.
At this milestone 33 offline tests covered review structure, single correction,
repeated-failure stopping and merged usage.

## Stage 4: graph nodes and persistent recovery

bench-graph-v1 was implemented; see [Workflow](langgraph_workflow.md).
The original loop remains a baseline.

- [Address pause, 13 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/8b2dd7f2-31cf-4194-b9bd-0e4f54e28dfc/run/8b2dd7f2-31cf-4194-b9bd-0e4f54e28dfc):
  collect → retrieve → check → clarify, zero model usage.
- [New-process resume, 12 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/edcb06d0-0c0f-48b3-9238-4e6b9c3bb075/run/edcb06d0-0c0f-48b3-9238-4e6b9c3bb075):
  after process exit, an explicit simulated unknown reply resumed generation,
  validation, review and finalize in the same thread.
- Local before/after comparison found identical evidence, facts and chunks;
  collection/retrieval ran once. User context did not become measured versions
  or configuration changes.
- [Live correction, 30 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/09f8a22c-a9b9-48a6-b9ab-1f241cc6916e/run/09f8a22c-a9b9-48a6-b9ab-1f241cc6916e):
  first review found a network overclaim; correct_report regenerated/reviewed successfully.

Offline coverage included one retrieval retry, escalation after insufficiency,
structural correction, repeated review failure, acquisition failure, archived
document exclusion, rebuilding after SQLite close, and version-drift rejection.
At that stage retrieval retry had only fake-model tests; the real index was not
artificially weakened. Tickets/approval were not yet implemented.

## Stage 5: local tickets

bench-graph-v2-tickets added explicit --ticket, drafts, edit/approve/cancel,
idempotent creation and retry after approved-creation failure. No automatic
migration of old checkpoints.

CLI validation simulated human actions, not authorization for real equipment:

- [Draft and pause, 29 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/01f29d5c-e5e4-4cde-9378-7a66c395ae7b/run/01f29d5c-e5e4-4cde-9378-7a66c395ae7b):
  initial retrieval missed support guidance and actually triggered refine_query;
  after coverage, diagnosis produced r1 awaiting approval.
- [Edit and reapprove, 6 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/2bb95682-7ff8-4a6f-af17-5203ee13f142/run/2bb95682-7ff8-4a6f-af17-5203ee13f142):
  explicit Demo validation notes produced r2; CLI rejected the old r1 hash.
- [Local creation, 6 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/7487670f-79b8-4022-8822-b88c5890a2d8/run/7487670f-79b8-4022-8822-b88c5890a2d8):
  exact r2 hash created DEMO-TKT-5e493b067c0f14eb8d982904.
  Reapproval returned the same ID. Editing/confirmation added no model usage.

SQLite is authoritative and JSON recoverable. No external support upload occurred.
The validation ticket's human notes explicitly stated demo-only, engineering
review required and no device changes authorized. Model-review limitations remain.

58 offline tests passed, including 13 ticket tests: exact approval, stale approval,
protected fields, cross-process edits/reapproval, cancellation, concurrent
deduplication, export repair, retry after commit but before checkpoint, and
exclusion of unreviewed inference in evidence-gap drafts. Tests found Windows
SQLite connections closing too late; explicit close-before-export fixed it.

## Stage 6: joint-response task

bench-graph-v3-motion adds explicit joint_response with three read-only tools,
demo-joint-response-v1 knowledge and a dedicated prompt. Initialization defaults
retain their task/scope. Older checkpoints are not migrated. Motion checks
required metric/troubleshooting sections as well as roles; a high-similarity
chunk alone cannot satisfy coverage.

Live Claude/LangSmith checks on 2026-11-08:

| Run | Result | Trace |
| --- | --- | --- |
| Baseline, motion-v3-baseline-final-1108 | 0% overshoot, 0.67 s settling and final error passed only for this action; no repeated load question | [24 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/7f96be20-e67f-4394-9342-1d8a3b1d70b3/run/7f96be20-e67f-4394-9342-1d8a3b1d70b3) |
| Oscillation, motion-v3-oscillation-1108 | 58.53% / 2.56 s failed; Kd change prioritized as hypothesis, not unique cause or tuning | [24 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/43ee6d3e-bddb-4000-8c05-07ff96a956b3/run/43ee6d3e-bddb-4000-8c05-07ff96a956b3) |
| Missing load, motion-v3-load-1108 start | check_evidence → clarify, zero model usage | [16 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/e24eefab-5640-4b01-ad47-a61271c1922e/run/e24eefab-5640-4b01-ad47-a61271c1922e) |
| Same thread, new process | Explicit demo unknown reply; 16.01% / 1.8 s failed, payload/inertia unknown; TEST-307 draft awaiting approval | [15 steps](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/121be7c7-79ed-4743-b5e0-f6d75a23243b/run/121be7c7-79ed-4743-b5e0-f6d75a23243b) |

Before/after evidence/facts/chunks matched; collection/retrieval ran once.
The reply remained unverified context; payload_record/equivalent_inertia gaps
remained. This live thread stopped at approval, without automatic creation.
Offline SQLite tests verified subsequent motion ticket creation through shared storage.

The first baseline run redundantly requested already-complete load records and
review missed it. Generation/review rules were strengthened to avoid invented
physical-assembly preconditions for complete offline tests; the final baseline
above stopped asking. Missing-load reports retain questions without another
blocking loop or a fabricated cause.

Live review of evaluation/cases/joint_response_review.json flagged motion_overclaim
and unsupported_claim for registered-as-current inertia, PD integral saturation
and automatic tuning; the bounded variant passed:
[5-step trace](https://eu.smith.langchain.com/o/ce8ddf52-4a70-4d3b-8c07-4fda19d97142/projects/p/dc01882f-97b4-463a-8c8a-15eec53b6a88/trace/722687eb-bbed-41d0-b07d-2927a6f80bd5/run/722687eb-bbed-41d0-b07d-2927a6f80bd5).
Reproduce with `python scripts/evaluate_review.py --case joint_response_review`,
using API credits. Scenario labels and expected answers are excluded from requests.

75 offline tests passed, covering task routing, wrong scope/missing requirement
sections, required-tool failure, SQLite resume without recollection, replies not
overwriting unknowns, retained draft gaps and approved local creation. Earlier
initialization/ticket tests and three fixture checks still passed. These finite
cases do not guarantee wording, causation or citation correctness for arbitrary
inputs. Later UI/ROS validation is recorded in [Dashboard](dashboard.md) and
[ROS bridge](ros_replay_bridge.md).
