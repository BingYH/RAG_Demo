# RAG & AI Workflow Demo

An AI technical-support workflow for a fictional robot test bench: grounded
knowledge answers, diagnostic evidence collection, human confirmation and local
support ticket creation.

## Project language

English is the default for all project-generated and maintained text:
documentation, plans, memory, instructions, AGENTS/SKILL files, prompts, comments,
docstrings, scripts, CLI messages and examples. See [AGENTS.md](AGENTS.md).
The Dashboard retains optional Chinese/English presentation, with English as the
default. Third-party clones/downloads, including references/repos/, remain
unchanged. Historical evidence/checkpoints/tickets are not rewritten.

## Technology

- **RAG** retrieves curated public-background and synthetic guidance.
- **LangGraph** manages state, conditional routes, bounded retries and human approval.
- **LangSmith** traces execution and supports fixed-case quality evaluation.

## Current status

For the interview, use the [under-ten-minute demonstration package](docs/interview_demo/README.md):
timed screen sequence, English speaking notes, engineering and architecture
diagrams, and a local saved-case readiness check.

For the interview, use the [under-ten-minute demonstration package](docs/interview_demo/README.md):
timed screen sequence, English speaking notes, engineering and architecture
diagrams, and a local saved-case readiness check.

The local bilingual Streamlit Dashboard shows curves, evidence, clarification/
resume, draft editing/approval and traces:

~~~powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
~~~

Open `http://127.0.0.1:8501`. English is selected by default; start a new English
thread for an interview presentation. Existing records retain original content.
See [Dashboard](docs/dashboard.md).

Implemented: Claude → LangSmith smoke test, CLI baseline, graph retrieval/
correction/SQLite recovery, drafts/approval/idempotent creation and bilingual UI.
No external ticket system is connected. See [Plan](RAG_DEMO_PLAN.md).
Synthetic diagnosis and local tickets need neither a physical arm nor a full ROS setup.

WSL 2 / Ubuntu 24.04 / ROS 2 Jazzy replay, subscriber collection and Windows HTTP
read-only adapters are also implemented. All three conditions completed actual
601-sample message delivery. The UI explicitly selects Local JSON or WSL ROS.
Live ROS-to-English-report/clarification/draft validation passed; offline resume
retains source without fallback. See [Dashboard](docs/dashboard.md),
[ROS bridge](docs/ros_replay_bridge.md), [WSL setup](docs/wsl_ros_setup.md).

`python scripts/verify_wsl_http.py` verifies a temporary cross-system probe only.
`python scripts/ros_replay_bridge.py --scenario joint_tracking_oscillation --verify-only`
starts actual replay, reads recomputed evidence and shuts down without model calls.

The joint-response extension includes three offline PD conditions, independent
retrieval, read-only facts, load clarification, review and approval. See
[Joint response](docs/joint_response_demo.md) and [Workflow](docs/langgraph_workflow.md).
Generate reproducible trajectories/PNGs at data/motion_reports/:

~~~powershell
.\.venv\Scripts\python.exe scripts/generate_motion_fixtures.py

# Oscillation diagnosis
.\.venv\Scripts\python.exe scripts/graph_bench.py --task joint_response --scenario joint_tracking_oscillation

# Missing load: clarify, then prepare a ticket; follow printed resume/approval commands
.\.venv\Scripts\python.exe scripts/graph_bench.py --task joint_response --scenario joint_tracking_load_unknown --ticket
~~~

Current workflow: bench-graph-v3-motion. Older checkpoints need new threads.
Initialization commands keep their existing task semantics.

## Reference material

[Sources](docs/sources.md) explains roles, reading order and mappings.
[Manifest](docs/source_manifest.json) records exact commits/file fingerprints.
Raw reference repositories are excluded from commits and translation.

[Bench definition](docs/demo_bench.md) describes components, fields, initial
scenarios and ticket boundaries. Five English initialization knowledge categories
are in knowledge/. Three states/logs and five read-only tools are documented in
[Simulator](simulator/README.md). Validate offline with
`python scripts/validate_fixtures.py`.

~~~powershell
python scripts/inspect_bench.py --scenario connection_timeout --tool read_connection_observations
~~~

## Data and configuration

Use public material and fully synthetic cases, never employer/customer internal
documents, logs or code. Label public provenance and synthetic content separately.
Keys come from environment variables and are never committed. Git ignores
virtual environments, local databases, runtime logs and external references.

## Minimal trace check: Windows PowerShell

Using Python 3.12 at the project root:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/smoke_trace.py
~~~

Configure ANTHROPIC_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING=true and
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com first. Process environment
takes precedence; on Windows, missing values are also read from current-user
environment variables. Keys are not printed.

Default model: claude-haiku-5-5, override ANTHROPIC_MODEL. Default trace project:
rag-demo-smoke; configured Agent ID selects its associated configuration.
Each run makes one paid model call and uploads a fixed synthetic prompt/answer
to LangSmith.

Success prints TRACE_OK, tokens, TRACE_VERIFIED and a trace link. Inspect the
outer claude-smoke-test and inner model input/output/timing/usage.
Remote read-back checks both records are visible.

## Knowledge and diagnostic tools

diagnose_bench.py remains the original tool-loop baseline.
For graph nodes and persistent pause/resume, prefer graph_bench.py:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario version_mismatch
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario connection_timeout
~~~

Address discrepancies pause and print a resume command. Use the same Thread ID
and --reply. SQLite state is under data/checkpoints/; no paid cloud deployment
is required.

For complete ticket handling:

~~~powershell
.\.venv\Scripts\python.exe scripts/graph_bench.py --scenario version_mismatch --ticket
~~~

After diagnosis, inspect the complete draft and Approve/Edit/Cancel commands.
Approval binds the current hash; editing requires reapproval. Local creation
writes data/tickets/ without external delivery.
See [Ticket workflow](docs/ticket_workflow.md) for editing, repeats and recovery.

To run the original baseline:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario connection_timeout
~~~

Claude selects five read-only tools and search_knowledge, then submit_analysis.
Code renders facts from original fields; Claude selects IDs and writes
interpretations/questions/steps. CLI prints calls, answer, total usage and trace.
submit_analysis submits diagnosis only, not a ticket. Traces contain model/tool
I/O, bound facts and retrieved chunks, read back through LangSmith v2 API.

~~~powershell
# Build/query the index without Claude or LangSmith
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --index-only

# Version mismatch
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario version_mismatch

# Healthy snapshot with a custom question
.\.venv\Scripts\python.exe scripts/diagnose_bench.py --scenario healthy --question "Check initialization and explain what is and is not established."
~~~

### Retrieval and execution boundaries

- Chroma stores data/index/. CPU all-MiniLM-L6-v2 ONNX embeddings download roughly
  80 MB on first use into data/models/ and are reused without embedding API fees.
- Initialization indexes only current demo-bench-v1 knowledge. Archived documents,
  references, fixtures, design docs and evaluation answers are excluded.
  Section chunks retain version, source IDs and paths. Changes select a new
  content-versioned index. Motion has its separate scope.
- Knowledge/queries and default answers are English. Chinese is optional through
  the Dashboard. Cosine distance ranks candidates, not truth or sufficiency.
- Scenarios are developer-selected, not model parameters. A run binds one immutable
  snapshot, not live acquisition or a real retest.
- The baseline permits at most six generation rounds and 20 calls including report
  submission. Structure/citation/review failures share one correction. There
  are at most two separate review calls. Limits, truncation and repeated failure
  stop explicitly.
- Facts bind tool, field path, original value, registry/runtime origin, evidence,
  snapshot and time. Models cannot supply fact names, values or evidence IDs.
  Registered/current version/address pairs prevent value merging or substitution.
- Pydantic rejects nonexistent facts, unreturned chunks, mixed snapshots and
  handwritten citations. Application-added citations guarantee a mapping exists,
  not that an inference is correct.
- Separate evidence_review compares report with facts/cited passages for network
  overclaims, redundant known-value questions, compatibility errors and direct
  contradictions. Specific failures permit one correction. Invalid reviewer
  output fails explicitly. Review can miss or falsely flag issues.
- Diagnosis makes multiple paid requests including review. Usage aggregates both.
  Local answers/calls/reviews/usage are ignored under data/runs/. Traces include
  evidence_review and its model child.
- The baseline is one diagnostic session. The graph adds clarification/approval,
  cross-process recovery, exact-content approval and idempotent local writes.
  --ticket explicitly requests a draft; otherwise diagnosis only.

### Offline validation

~~~powershell
.\.venv\Scripts\python.exe scripts/check_language.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_fixtures.py
~~~

Unit tests use fake models without API access. They check tools, isolation,
document filters, result delivery, field-source binding, structured corrections
and budgets. Initial embedding download/live-model end-to-end checks are separate.

evaluation/cases/version_mismatch_review.json contains bad/bounded variants,
excluded from RAG. Run a paid review regression:

~~~powershell
.\.venv\Scripts\python.exe scripts/evaluate_review.py
~~~

It checks network_overclaim, redundant_question and compatibility_error detection,
plus acceptance of the bounded variant. Expected labels are not sent to the model;
results go under evaluation/results/. Two examples passing is not full-set accuracy.
