# RAG Demo plan: from knowledge answers to traceable workflows

## 1. Demonstration positioning

Build an evidence-based, controlled and evaluable AI technical-support workflow:
retrieve knowledge, clarify gaps, choose next steps from evidence, wait for human
confirmation, call business tools and record observable execution for evaluation.

This project demonstrates AI workflow design, tools, human participation,
observability and evaluation. Separate `Python_Proj` work demonstrates Python
programming, test automation and data analysis.

### Technology responsibilities

- **RAG** supplies verifiable domain knowledge.
- **LangGraph** manages shared state, branches, bounded retries, human
  confirmation, pause/resume and business tools.
- **LangSmith** traces retrieval, nodes and tools, locates failures and compares
  fixed evaluations for regressions, quality, latency and cost.

The narrative moves from answering questions to advancing work with evidence,
then improving through traceability and evaluation.

### Relevance to the target role

Choose an understandable engineering scenario reflecting technical support,
structured analysis and demonstrations in the Agile Robots Mechatronics Test
Engineer role. Show how knowledge, process and tools form a reliable application;
Section 2 defines the topic.

Make answer sources, missing/conflicting evidence, human involvement and
verification of improvements visible. AI traces show inputs, evidence, routes
and tools. Requirement-to-test traceability still needs explicit engineering
identifiers and relationships.

### Initial supporting components

| Component | Purpose |
| --- | --- |
| LLM and embedding model | Understanding, answers/structured output and document vectors; provider/model selection belongs to implementation |
| Local Chroma | Chunk storage/retrieval with source, version and applicability metadata |
| Pydantic | Clarification, evidence, parameters and draft schemas; structural validity is not correctness |
| SQLite checkpointer | Save graph state for confirmation and cross-process recovery |
| Streamlit | Conversation, citations, current state, drafts and confirmation |
| Simulated business tool | Create an actual local ticket/record after approval, return an ID and prevent duplicates on resume |

LangSmith covers tracing and evaluation; no extra evaluation platform is needed.
Consider hybrid retrieval, reranking, MCP and FastAPI only for clear needs.
Start with direct tools and one graph.

## 2. Knowledge topic

### Selected: robot test-bench initialization and communication failures after an update

Combine ARRK-inspired structured investigation, public robotics material and
fully synthetic cases in a shareable, reproducible workflow. ARRK supplies
methodological inspiration, public docs supply verifiable knowledge and a
synthetic bench supplies a controlled environment. The independent design does
not represent ARRK, customers or Agile Robots systems.

### Experience and initial scope

Use bring-up, software/hardware version matching, network diagnosis and quality
analysis methods: separate product, software-monitoring and test-environment
hypotheses before choosing verification. A fault report is not proof of hardware damage.

Initial story: after a workstation update, the bench cannot initialize and times
out. The assistant checks context, retrieves applicable material, reads simulated
diagnostics and proposes next steps. If unresolved, prepare a support ticket for approval.

Overtemperature/measurement-chain investigation remains a later candidate,
drawing on thermal tests, reference sensors and cooling checks. Power-fault
injection and power measurement are outside the initial main story.

Implemented extension: **joint overshoot/oscillation investigation** using offline
single-joint PD position response, zero integral, and baseline, low-damping and
missing-load conditions. Code generates trajectories/metrics; the assistant
collects configuration, response and context, retrieves guidance and organizes
hypotheses without assuming PID is the root cause or tuning automatically.
See [Joint response](docs/joint_response_demo.md). Claude/LangGraph supports
load clarification, review and ticket approval. At that milestone 75 offline
tests and live runs/trace read-back for all three conditions passed.

The user recalls a first-interview system-test lead mentioning PID information
or actions in a robot functional-test example. Control-theory PID is the provisional
interpretation; exact wording/tests remain unconfirmed, not verified job
requirements. This extension does not replace the initialization story.

Experience references:

- `../JD_Dashboard/Info_Input/WorkExperience_ARRK/WorkExperience_ARRK/arguments_Verteidigung.txt`
- `../JD_Dashboard/Taget_Job/Test_Engineer/Agile_Robots_Mechatronics_Test_Engineer/InterviewPreperation/ARRK_Technical_Discussion_EN.md`

### Data boundaries

- Rewrite generic methods as synthetic cases rather than renaming internal material.
- Independently design structures, versions, thresholds, fault mappings, logs
  and conclusions; label all synthetic demo data.
- Internal documents, raw logs, code, screenshots and customer identifiers stay
  outside the corpus, model requests and traces.
- Retain public links, versions and scope. Distinguish demo rules from vendor
  instructions; never attribute fictional conclusions to vendors.
- Describe an independent experience-inspired demo, not an ARRK/target-company deployment.

### Public/open-source references

| Source | Concepts | Role |
| --- | --- | --- |
| [Official franka_ros2](https://github.com/frankarobotics/franka_ros2) | Integration, configuration, troubleshooting | Technical background; full ROS deployment was not initially required |
| [FCI troubleshooting](https://frankarobotics.github.io/docs/troubleshooting.html) | Connection/communication timeouts, network checks, incompatibility | Priority knowledge |
| [Software compatibility](https://frankarobotics.github.io/docs/compatibility.html) | System/client relationships | Version clarification and scope checks |
| [selfpatch/ros2_medkit](https://github.com/selfpatch/ros2_medkit) | Fault/status/snapshot REST APIs and hardware-free diagnosis | Tool-interface inspiration; possible later integration |
| [earosenfeld/robot-test-bench](https://github.com/earosenfeld/robot-test-bench) | Motor/sensor/servo simulation, sample data and Dashboard | Optional simulation inspiration |

Initially only introductions were reviewed, without downloading/running/validating.
Current snapshots are in [Sources](docs/sources.md). These are not ready-made
bench-maintenance assistants. Reuse requires version, license and runtime checks.
Prioritize public docs and project-owned tools so setup does not become the main story.

### Natural AI workflow

1. Clarify model, system/client versions, complete error and update scope.
2. Retrieve troubleshooting, compatibility and synthetic procedures; check sources/scope.
3. Read versions, connections and logs; separate runtime evidence from static knowledge.
4. Fill gaps or explain conflicts; cite recommendations and distinguish facts,
   hypotheses and verification.
5. Draft facts, checks, open issues and attachments; allow edits, confirm, create
   and return a deduplicated ticket ID.
6. Trace/evaluate required questions, applicable citations, tools and unsupported
   hardware-damage claims.

RAG supplies guidance, tools supply state, LangGraph coordinates, and LangSmith
observes/evaluates. Initial actions are read-only diagnosis and local ticket creation.

### Knowledge planning

Plan 10–15 short documents on structure, initialization, compatibility,
communication, logs, synthetic cases and escalation/ticket rules. Mark old/current
versions and scope. For each demo question define required sources, clarification,
tools and expected routes to form evaluation ground truth.

## 3. Core question

> After a workstation update, the robot bench cannot initialize and reports a
> connection timeout. Help investigate; prepare a support ticket if unresolved.

Combining knowledge and action demonstrates clarification, cross-document
retrieval, evidence checks and confirmation.

## 4. LangGraph orchestration

Implemented: diagnostic graph, one retrieval retry, clarification/cross-process
resume, validation/one correction, local drafts/edit/approve/cancel/idempotent
creation. See [Current workflow](docs/langgraph_workflow.md) and
[Ticket rules](docs/ticket_workflow.md). No external ticket system is connected.

Original conceptual flow; actual nodes are in the workflow document:

~~~mermaid
flowchart TD
    A[User question] --> B[Identify task and required context]
    B -->|Missing versions or environment| C[Clarify]
    C --> B
    B -->|Context available| D[Retrieve knowledge]
    D --> E[Check coverage and version scope]
    E -->|Insufficient; retry available| F[Rewrite or split query]
    F --> D
    E -->|Still insufficient or conflicting| G[Explain gaps and escalate]
    E -->|Sufficient| H[Generate cited recommendations]
    H --> I{Action requested?}
    I -->|No| J[Return answer]
    I -->|Yes| K[Draft ticket]
    K --> L[Human confirmation]
    L --> M[Call simulated business tool]
~~~

### Three important branches

1. Clarify missing versions/environment, then continue with shared state.
2. Focus/split retrieval queries, for example causes versus escalation conditions;
   initially plan one or two extra rounds, then explain remaining gaps.
3. Draft, pause with `interrupt()`, then resume and execute after confirmation.

Coverage, version applicability and contradictions matter beyond similarity.

### State and recovery

Shared state should include question, versions/environment, clarification,
queries/chunks, retries/routes, answer, draft and confirmation.
Persistent checkpointers and `thread_id` support cross-process recovery.
Prevent duplicate business actions. Nodes, conditional edges and shared state
suffice; multiple agents are unnecessary initially.

## 5. LangSmith monitoring and traceability

| Level | Data | Question |
| --- | --- | --- |
| Individual trace | Original/rewritten queries, chunks, node I/O, tools, timing | How was this answer produced? |
| Aggregate | Latency, errors, tokens, available cost statistics, quality metrics | How is the system operating? |
| Evaluation | Baseline and graph on identical questions | Did orchestration improve results? |

Record document/chunk IDs and versions; routes, gaps and retry reasons/counts;
model, prompt version and thread; citations, abstention/escalation, ticket state
and feedback. Custom retrieval/routing needs explicit instrumentation.
Observable inputs, evidence, decisions and execution are not a complete
reconstruction of internal model reasoning.

## 6. Evaluation design

Prepare 15–20 questions covering factual lookup, synthesis, missing context,
obsolete/current conflicts, insufficient initial retrieval, absent knowledge,
and ticket requests requiring confirmation. Keep model/corpus consistent for
baseline/graph comparison and record configuration differences.

| Metric | Check |
| --- | --- |
| Expected retrieval | Labeled document/chunk IDs |
| Grounded answer | Human plus model review |
| Supporting citations | Passage versus claim |
| Clarification/abstention/escalation | Expected behavior versus trace |
| Tool execution | Approval, parameters and calls |
| Latency/cost | Runtime statistics and cost of quality gains |

Start offline before online sampling. Measure benefits/tradeoffs rather than
assuming orchestration is better.

## 7. Live presentation: 8–10 minutes

The current role-focused PD demonstration is prepared in the
[interview package](docs/interview_demo/README.md), targeting 9:15 with a 45-second
reserve. It provides diagrams, English notes and an exact screen sequence. The
table below retains the original conceptual presentation plan; use the interview
package for the current rehearsable route.

| Time | Activity | Value |
| --- | --- | --- |
| 1 minute | Bench/documents | Business context |
| 2 minutes | Ordinary answer with citations | Grounding |
| 2 minutes | Missing-version case, clarification/retrieval retry | Branching/state |
| 2 minutes | Draft, approve, local tool | Action |
| 2–3 minutes | Trace and prepared evaluation | Debugging/measurement |

Prepare a first-retrieval-insufficient, second-retrieval-success trace; explain
queries, chunks, routing and final references. Verify reproducible branches.
Run evaluations beforehand. Saved traces can back up network/service failures,
explicitly identified as historical records.

## 8. Initial scope

- One Markdown bench-troubleshooting corpus.
- Baseline RAG comparison.
- One graph with clarification, retrieval retry and human confirmation.
- One simulated ticket tool.
- Simple UI for answers, citations, nodes and drafts.
- LangSmith tracing/evaluation questions.

Later directions: external tickets, persistence, more sources and online quality
monitoring. Persistent recovery has since been implemented.

## 9. Official references

- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangSmith observability](https://docs.langchain.com/langsmith/observability)
- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
