---
doc_id: support.ticket_workflow
title: Support escalation and confirmed ticket creation
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-bench-v1]
source_ids: []
---

# Support escalation and confirmed ticket creation

## Applicability

This is a project-defined support workflow, not a Franka, ARRK or customer procedure.

Prepare a draft when the user requests it or when unresolved evidence requires engineering support. A draft may explicitly retain an unknown root cause. Do not create a ticket automatically just because the assistant finds a possible anomaly.

## Draft content

Include bench ID, symptom and incident context, startup attempt and snapshot identifiers, installed and observed versions (label registered values separately), loaded endpoint, completed checks with evidence IDs, applicable knowledge document references, unresolved gaps and proposed next actions. List only evidence attachments that actually exist; do not invent uploaded files or issue owners.

Separate facts from hypotheses. Failed tool acquisition belongs in the evidence-gap section. A normal snapshot does not invalidate an earlier reported fault; include the time mismatch if unresolved.

## Confirmation

Show the complete draft for review. The user can edit, confirm or cancel it. Any content change invalidates previous approval. The workflow must associate approval with the exact draft revision; a model-supplied boolean is not approval.

Only the confirmed creation tool writes a local ticket under `data/tickets/` and returns its ID. Repeating the same confirmed request after recovery returns the existing ticket rather than creating another. Cancellation creates no ticket. Until an ID is returned, describe the result as a draft, not a submitted ticket.

## Boundaries

The assistant may recommend an engineer verify a configuration or plan a retest. It cannot execute motion, tune PID gains, disable safety rules, reconfigure networking, clear faults, restart services or install software in v1. A local demo ticket is not sent to an external support service.
