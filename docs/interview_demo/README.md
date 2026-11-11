# Interview demonstration: evidence-based joint-response investigation

**Target: 9 minutes 15 seconds, with 45 seconds of reserve.**

## The message

> I translate test requirements into reproducible checks, investigate failures
> using configuration and test context, and combine deterministic Python with
> an observable AI workflow to prepare an engineering decision.

The main example is the offline single-joint **PD** response: Ki=0, overshoot
58.53%, settling time 2.56 s. The missing-load example is a short contrast showing
how investigation changes when evidence is incomplete. It is a separate test,
not a repaired version or a retest of the oscillation case.

## Presentation materials

- [English and Chinese PowerPoint decks](Presentation/README.md): 10 main slides,
  six hidden appendix slides and language-specific speaker notes. The current
  decks explain project structure and the AI workflow first, then demonstrate
  the PD case. Use their embedded notes for the current speaking sequence;
  the Markdown run of show and speaking notes retain the earlier case-first route.

- [Timed screen sequence and setup](run_of_show.md): what to open, click and skip.
- [English speaking notes and follow-up answers](speaker_notes.md).
- [Chinese presentation documents](Chinese/README.md): separate translations of this guide, the run of show and the speaking notes.
- [Project folder map](folder_structure.md), with editable [Mermaid source](folder_structure.mmd).
- [Standalone folder viewer](folder_structure.html): offline full screen, zoom and collapsible sections.
- [Engineering investigation diagram](engineering_workflow.svg), with editable
  [Mermaid source](engineering_workflow.mmd).
- [Python, ROS and AI architecture diagram](system_architecture.svg), with
  editable [Mermaid source](system_architecture.mmd).

Show the engineering diagram briefly at the opening. Show the architecture only
after the audience has seen the engineering result. SVGs open directly in a
browser and can be inserted into future slides. These are presentation summaries;
the [actual graph](../langgraph_workflow.md) contains additional nodes and bounded
retry/correction paths.

## Relevance to the saved job description

Basis: pages 1–2 of the locally saved *Mechatronics Test Engineer (m/f/d)* posting
in `JD_Dashboard/Taget_Job/Test_Engineer/Agile_Robots_Mechatronics_Test_Engineer/`.
This is a mapping to that saved posting, not a claim about the team's current
internal benches or confirmed interview questions.

| Responsibility in the posting, paraphrased | Demonstrated evidence | Explain your decision |
| --- | --- | --- |
| Develop test-bench software | Python fixtures, metric calculation, read-only adapters and workflow | Keep measurement decisions reproducible and separate from generated prose |
| Data acquisition and analysis | 601-sample trajectory, ROS collection, Windows HTTP validation | Bind analysis to a complete, identified snapshot |
| Review and verify requirements | Explicit overshoot/settling/error criteria | Distinguish a failed transient response from final-position accuracy |
| Evaluate results and give development feedback | Configuration change, current conditions, cited hypothesis and proposed retest | Prioritize checks without prematurely declaring a unique cause |
| Document test/calibration procedures | Versioned test procedure and requirements | This demonstrates a test procedure, not an implemented calibration process |
| Support customers and colleagues | Clear report, missing-context question and reviewed draft | Communicate actionable next steps and unresolved evidence |
| Deliver demo presentations | Curves first, short narrative and supporting trace | Adapt detail to the audience and explain limits accurately |
| Unix/Python and system integration | WSL Bash/ROS plus Windows Python/Streamlit | Explain the data contract and failure behavior across systems |

Physical construction/commissioning, C++, EtherCAT, calibration and standards
compliance are not established by this demo. Discuss actual experience separately.
ROS is an integration choice here; it is not listed as a requirement in the saved
posting. The PD interview reference remains the user's recollection, not a
confirmed specific test requirement.

## Three engineering conclusions to make visible

1. The response fails two transient requirements even though the final-window
   error passes. Reaching the target eventually is insufficient.
2. Kd changed from 0.85 to 0.10. Lower damping is a supported priority hypothesis;
   an engineer still checks change intent, conditions and a controlled retest.
3. Missing current load/inertia cannot be replaced by registered baseline values.
   The workflow asks, retains unknowns and can continue with an explicit gap.

## Three software decisions to make visible

1. Python computes values, integrity checks and pass/fail decisions; the LLM
   selects facts and explains evidence. The application renders bound values/citations.
2. LangGraph owns branching, one clarification, bounded retrieval/correction and
   approval. LangSmith makes execution and review outcomes inspectable.
3. Read-only evidence collection is separate from the approved write of a local
   ticket. Human approval binds the exact draft hash; it does not authorize motion.

## Scope statement

This is an independently designed synthetic test-support demo, inspired by
transferable engineering methods and public material. It does not represent an
ARRK/customer/Agile Robots production system. PD simulation, demo thresholds and
ROS replay are not physical robot acceptance, automatic tuning or real-time
control validation. Model review reduces some errors but does not prove correctness.

## Demonstration modes

Use **verified saved runs** as the default for a strict ten-minute slot, explicitly
identified as historical executions. The existing English oscillation case uses
Local JSON; the existing English missing-load report/draft uses WSL ROS replay.
Do not imply those are the same source or the same test. A fresh missing-load
clarification can be demonstrated without a model call.

Live report generation is optional after rehearsal. Cap visible waiting at
30 seconds, then switch to a saved run with a clear explanation. Do not repeatedly
start diagnoses. The rehearsal, not this document, will establish actual delivery time.
