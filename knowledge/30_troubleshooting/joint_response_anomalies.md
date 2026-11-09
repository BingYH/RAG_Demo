---
doc_id: troubleshooting.joint_response_anomalies
title: Evidence-led investigation of single-joint overshoot and oscillation
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-joint-response-v1]
source_ids: []
---

# Evidence-led investigation of single-joint overshoot and oscillation

## Establish the observation before the cause

This is a synthetic support procedure, not a manufacturer fault table. First identify the session-bound test, action and recorded conditions. Use procedure.joint_response_test to interpret metrics and thresholds. An exceeded response requirement establishes an observation for this action, not a unique root cause. Do not infer a faulty motor or incorrect PID gains solely from overshoot. This demo implements PD with no integral action; do not diagnose integrator windup here.

## Compare the current configuration with its baseline

Read the current mode, Kp/Ki/Kd, limits, revision and recorded change history. Label registered baseline values separately. In this project's inertia/damping model the negative velocity term contributes damping. A recorded reduction in Kd with the same documented test conditions supports prioritizing configuration verification as a hypothesis. It does not prove all other faults are absent, prove a hardware diagnosis or authorize restoring gains. Do not choose replacement gains from the symptom alone.

## Check load and test conditions before blaming gains

Similar overshoot can result from different relationships between controller and plant. Review payload/fixture records, current equivalent inertia if recorded, target action, sampling, limits and any changes. When current payload or inertia is null, do not copy the registered baseline into it. Matching gains do not establish matching physical conditions. Unknown load does not prove load increased or that it caused the anomaly. State the response failure, identify the missing conditions and retain alternative hypotheses.

## Targeted clarification

Ask what tool/fixture and load were used for this test, whether they changed, and whether there is a corresponding test or configuration record. Do not ask again for gains, action or results already returned by tools. Treat user statements as unverified context unless a new evidence source validates them. If the user cannot supply the missing information, summarize the gap and proceed to a limited report or support draft; do not repeatedly ask the same question or manufacture a root cause.

## Bounded next actions

Recommend that an engineer verify the configuration change record and the load/test setup against the applicable test baseline, then plan a supervised repeat with newly recorded evidence. If current context is incomplete, request its verification before asserting a parameter comparison is decisive. Do not propose an automatic parameter sweep, execute motion, change limits, clear faults or claim an immutable fixture has been repaired. This workflow has read-only evidence tools and optionally confirmed local ticket creation.

## Support draft and human confirmation

When requested, prepare a draft containing bench/test/snapshot IDs, the action and procedure, current configuration and labelled registered baseline, metric/requirement comparisons, trajectory ID/hash and calculation versions, completed checks, knowledge references, unresolved context and proposed next checks. Separate facts from hypotheses; unknown root cause is acceptable. List only attachments that exist. A new draft needs human review; editing invalidates old approval. Confirmation authorizes local ticket creation only, not motion or tuning. Do not say a ticket was created until its ID is returned.

## Normal and insufficient-evidence outcomes

When all response items pass and recorded conditions are complete, report a pass for this recorded single-joint action only. If a user reports another event, clarify its time and reproducibility rather than dismissing it. If a tool fails or a recording is not_evaluable, describe the acquisition/coverage gap, not a proven robot defect. Keep tool success, response pass/fail and test context completeness as separate results. Every interpretation must cite the actual evidence and applicable document chunks.
