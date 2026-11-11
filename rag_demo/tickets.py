"""Local ticket drafts, exact-content approval and transactional idempotency."""

import copy
import hashlib
import json

import os
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from rag_demo.ui_i18n import translate

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
EDITABLE_FIELDS = {"title", "description", "requested_support", "engineer_notes"}


class EditableTicket(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    requested_support: str = Field(min_length=1, max_length=2000)
    engineer_notes: str = Field(max_length=2000)


def content_hash(draft: dict) -> str:
    encoded = json.dumps(draft, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_draft(state: dict) -> dict:
    facts = list(state["facts"].values())
    reviewed = state.get("diagnosis_status") == "completed"
    report = state.get("report", {}) if reviewed else {}
    references = {chunk for claim in report.get("interpretations", []) for chunk in claim["chunk_ids"]}
    snapshots = {f["snapshot_id"] for f in facts}
    attempts = {r["data"]["startup_attempt_id"] for r in state["evidence"].values()
                if isinstance(r.get("data"), dict) and r["data"].get("startup_attempt_id")}
    tests = {r["data"]["test_id"] for r in state["evidence"].values()
             if isinstance(r.get("data"), dict) and r["data"].get("test_id")}
    if len(snapshots) > 1 or len(attempts) > 1 or len(tests) > 1:
        raise ValueError("Cannot draft a ticket from mixed snapshots or startup attempts.")
    language = state.get("output_language") or report.get("language", "en")
    editable = EditableTicket(title="BENCH-001 support request" if language == "en" else translate('BENCH-001 support request', 'zh'), description=state["question"],
        requested_support="Review the collected evidence and configuration, resolve remaining gaps and assess the next verification steps."
        if language == "en" else translate('Review the collected evidence and configuration, resolve remaining gaps and assess the next verification steps.', 'zh'), engineer_notes="")
    return {
        "schema_version": "1.1", "revision": 1, "bench_id": "BENCH-001", "language": language,
        "task_type": state.get("task_type", "initialization"), "test_id": next(iter(tests), None),
        "data_source": state.get("data_source", "local_json"), "source_metadata": copy.deepcopy(state.get("source_metadata", {})),
        "snapshot_id": next(iter(snapshots), None), "startup_attempt_id": next(iter(attempts), None),
        **editable.model_dump(), "user_context_unverified": state.get("user_context", ""),
        "diagnosis_status": state.get("diagnosis_status"),
        "facts": copy.deepcopy(facts), "completed_checks": copy.deepcopy(state["evidence"]),
        "interpretations": copy.deepcopy(report.get("interpretations", [])),
        "unresolved_questions": copy.deepcopy(report.get("questions", [])),
        "proposed_next_steps": copy.deepcopy(report.get("next_steps", [])),
        "evidence_gaps": ([state["error"]] if not reviewed and state.get("error") else []) + [
            f"{f['field']}: {f['unavailable_reason']} [{f['evidence_id']}]" for f in facts if f.get("unavailable_reason")],
        "knowledge_version": state["knowledge_version"],
        "knowledge_references": [copy.deepcopy(state["chunks"][key]) for key in sorted(references)],
        "attachments": [], "notice": "Synthetic local demo ticket; not sent to any external support service.",
    }


def validate_decision(draft: dict, decision: dict) -> None:
    if not isinstance(decision, dict) or decision.get("action") not in {"approve", "edit", "cancel"}:
        raise ValueError("Use an explicit approve, edit or cancel decision.")
    action = decision["action"]
    allowed = {"action"} if action == "cancel" else {"action", "draft_hash"}
    if action == "edit":
        allowed.add("edits")
    if set(decision) != allowed:
        raise ValueError("Decision arguments do not match the selected action.")
    if action != "cancel" and decision["draft_hash"] != content_hash(draft):
        raise ValueError("Draft changed or approval token is stale. Review the current draft before confirming.")
    if action == "edit":
        edits = decision["edits"]
        if not isinstance(edits, dict) or not edits or not set(edits) <= EDITABLE_FIELDS:
            raise ValueError("Only title, description, requested_support and engineer_notes can be edited.")
        editable = {key: draft[key] for key in EDITABLE_FIELDS}
        editable.update(edits)
        EditableTicket.model_validate(editable)
        if any(not editable[key].strip() for key in ("title", "description", "requested_support")):
            raise ValueError("Title, description and requested support cannot be blank.")


def revise_draft(draft: dict, decision: dict) -> dict:
    validate_decision(draft, decision)
    if decision["action"] != "edit":
        raise ValueError("A draft revision requires an edit decision.")
    revised = copy.deepcopy(draft)
    revised.update(decision["edits"])
    revised["revision"] += 1
    return revised


def approval_record(thread_id: str, draft: dict) -> dict:
    return {"source": "user_interrupt", "thread_id": thread_id, "draft_revision": draft["revision"],
            "draft_hash": content_hash(draft), "approved_at": datetime.now(timezone.utc).isoformat()}


def verify_approval(thread_id: str, draft: dict, approval: dict) -> None:
    if not isinstance(approval, dict) or (approval.get("source"), approval.get("thread_id"),
        approval.get("draft_revision"), approval.get("draft_hash")) != (
            "user_interrupt", thread_id, draft["revision"], content_hash(draft)):
        raise ValueError("Ticket creation requires approval of this exact thread and draft revision.")


class TicketStore:
    """SQLite is authoritative; JSON files are recoverable exports of committed records."""

    def __init__(self, root: Path | None = None):
        self.root = root or ROOT / "data" / "tickets"

    def _export(self, record: dict) -> Path:
        destination = self.root / (record["ticket_id"] + ".json")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.root,
                                              suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination

    def create(self, thread_id: str, draft: dict, approval: dict) -> dict:
        verify_approval(thread_id, draft, approval)
        draft_hash = content_hash(draft)
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.root / "tickets.sqlite3", timeout=20)) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY, thread_id TEXT NOT NULL,
                draft_revision INTEGER NOT NULL, draft_hash TEXT NOT NULL, record_json TEXT NOT NULL,
                UNIQUE(thread_id, draft_revision))""")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT draft_hash, record_json FROM tickets WHERE thread_id=? AND draft_revision=?",
                                     (thread_id, draft["revision"])).fetchone()
            reused = row is not None
            if row:
                if row[0] != draft_hash:
                    raise ValueError("An existing ticket has different content for this thread and draft revision.")
                record = json.loads(row[1])
            else:
                token = hashlib.sha256(f"{thread_id}:{draft['revision']}".encode()).hexdigest()[:24]
                record = {"ticket_id": "DEMO-TKT-" + token, "status": "created_locally",
                          "created_at": datetime.now(timezone.utc).isoformat(), "thread_id": thread_id,
                          "draft_hash": draft_hash, "approval": copy.deepcopy(approval), "draft": copy.deepcopy(draft)}
                connection.execute("INSERT INTO tickets VALUES (?, ?, ?, ?, ?)", (
                    record["ticket_id"], thread_id, draft["revision"], draft_hash,
                    json.dumps(record, ensure_ascii=False)))
            connection.commit()
        # If export fails after commit, the same approved request safely repairs the export.
        path = self._export(record)
        return {"ticket_id": record["ticket_id"], "status": record["status"],
                "draft_revision": draft["revision"], "draft_hash": draft_hash,
                "created_at": record["created_at"], "file_path": str(path), "reused": reused}

    def get(self, ticket_id: str) -> dict:
        if not re.fullmatch(r"DEMO-TKT-[0-9a-f]{24}", ticket_id):
            raise ValueError("Invalid local ticket ID.")
        database = self.root / "tickets.sqlite3"
        if not database.is_file():
            raise ValueError("Local ticket database is missing.")
        with closing(sqlite3.connect(database)) as connection:
            row = connection.execute("SELECT record_json FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if not row:
            raise ValueError("Local ticket not found.")
        return json.loads(row[0])


def render_draft(draft: dict, language: str | None = None) -> str:
    language = language or draft.get("language", "en")
    def text(zh, en):
        return en if language == "en" else zh
    labels = {
        "heading": text(translate('Ticket draft', 'zh'), "Ticket draft"),
        "identity": text(translate('Bench / snapshot / test', 'zh'), "Bench / snapshot / test"),
        "description": text(translate('Description', 'zh'), "Description"),
        "support": text(translate('Requested support', 'zh'), "Requested support"),
        "notes": text(translate('Engineer notes (human input)', 'zh'), "Engineer notes (human input)"),
        "context": text(translate('User context (unverified)', 'zh'), "User context (unverified)"),
        "facts": text(translate('Facts and sources', 'zh'), "Facts and sources"),
        "interpretation": text(translate('Interpretation (model inference)', 'zh'), "Interpretation (model inference)"),
        "gaps": text(translate('Open issues and next steps', 'zh'), "Open issues and next steps"),
        "checks": text(translate('Completed checks and knowledge references', 'zh'), "Completed checks and knowledge references"),
    }
    none = text(translate('None', 'zh'), "None")
    lines = [f"## {labels['heading']} r{draft['revision']}: {draft['title']}",
             text(translate('Data source', 'zh'), "Data source") + ": " + draft.get("data_source", "local_json"),
             f"{labels['identity']}: {draft['bench_id']} / {draft['snapshot_id']} / {draft.get('test_id') or draft.get('startup_attempt_id')}",
             labels["description"] + ": " + draft["description"], labels["support"] + ": " + draft["requested_support"],
             labels["notes"] + ": " + (draft["engineer_notes"] or none),
             labels["context"] + ": " + (draft["user_context_unverified"] or none), "\n### " + labels["facts"]]
    for fact in draft["facts"]:
        val = json.dumps(fact["value"], ensure_ascii=False)
        if fact["unavailable_reason"]:
            val = text(translate('Unknown', 'zh'), "Unknown") + " (" + fact["unavailable_reason"] + ")"
        elif fact["value"] is None:
            val = none
        lines.append(f"- {fact['labels'][1 if language == 'en' else 0]}: {val} [{fact['evidence_id']}]")
    lines.append("\n### " + labels["interpretation"])
    facts = {f["fact_id"]: f for f in draft["facts"]}
    for claim in draft["interpretations"]:
        refs = list(dict.fromkeys([facts[f]["evidence_id"] for f in claim["fact_ids"]] + claim["chunk_ids"]))
        lines.append("- " + claim["text"] + " " + "".join(f"[{ref}]" for ref in refs))
    if not draft["interpretations"]:
        lines.append("- " + text(translate('No reviewed interpretation; evidence gaps only.', 'zh'), "No reviewed interpretation; evidence gaps only."))
    lines.append("\n### " + labels["gaps"])
    lines += ["- " + i for i in draft["unresolved_questions"] + draft["evidence_gaps"] + draft["proposed_next_steps"]] or ["- " + none]
    lines.append("\n### " + labels["checks"])
    for name, observation in draft["completed_checks"].items():
        lines.append(f"- {name}: {observation['status']} [{observation.get('evidence_id', 'no evidence ID')}]")
    lines += ["- " + c["chunk_id"] for c in draft["knowledge_references"]]
    lines.append(text(translate('Attachments: none. Raw checks and full fields are in the draft JSON. Ticket creation is determined by the workflow receipt; nothing is sent externally.', 'zh'),
        "Attachments: none. Raw checks and full fields are in the draft JSON. Ticket creation is determined by the workflow receipt; nothing is sent externally."))
    return "\n".join(lines)
