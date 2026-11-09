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
    language = state.get("output_language") or report.get("language", "zh")
    editable = EditableTicket(title="BENCH-001 support request" if language == "en" else "BENCH-001 技术支持请求", description=state["question"],
        requested_support="Review the collected evidence and configuration, resolve remaining gaps and assess the next verification steps."
        if language == "en" else "请核查已收集的证据与配置，确认未解决事项并评估下一步验证。", engineer_notes="")
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
    language = language or draft.get("language", "zh")
    def text(zh, en):
        return en if language == "en" else zh
    labels = {
        "heading": text("\u5de5\u5355\u8349\u7a3f", "Ticket draft"),
        "identity": text("\u53f0\u67b6 / \u5feb\u7167 / \u6d4b\u8bd5", "Bench / snapshot / test"),
        "description": text("\u95ee\u9898\u63cf\u8ff0", "Description"),
        "support": text("\u8bf7\u6c42\u652f\u6301", "Requested support"),
        "notes": text("\u5de5\u7a0b\u5e08\u5907\u6ce8\uff08\u4eba\u5de5\u8f93\u5165\uff09", "Engineer notes (human input)"),
        "context": text("\u7528\u6237\u80cc\u666f\uff08\u672a\u9a8c\u8bc1\uff09", "User context (unverified)"),
        "facts": text("\u4e8b\u5b9e\u4e0e\u6765\u6e90", "Facts and sources"),
        "interpretation": text("\u8bca\u65ad\u89e3\u8bfb\uff08\u6a21\u578b\u63a8\u65ad\uff09", "Interpretation (model inference)"),
        "gaps": text("\u5f85\u89e3\u51b3\u4e8b\u9879\u4e0e\u5efa\u8bae", "Open issues and next steps"),
        "checks": text("\u5df2\u6536\u96c6\u68c0\u67e5\u4e0e\u77e5\u8bc6\u5f15\u7528", "Completed checks and knowledge references"),
    }
    none = text("\u65e0", "None")
    lines = [f"## {labels['heading']} r{draft['revision']}: {draft['title']}",
             text("数据源", "Data source") + ": " + draft.get("data_source", "local_json"),
             f"{labels['identity']}: {draft['bench_id']} / {draft['snapshot_id']} / {draft.get('test_id') or draft.get('startup_attempt_id')}",
             labels["description"] + ": " + draft["description"], labels["support"] + ": " + draft["requested_support"],
             labels["notes"] + ": " + (draft["engineer_notes"] or none),
             labels["context"] + ": " + (draft["user_context_unverified"] or none), "\n### " + labels["facts"]]
    for fact in draft["facts"]:
        val = json.dumps(fact["value"], ensure_ascii=False)
        if fact["unavailable_reason"]:
            val = text("\u672a\u77e5", "Unknown") + " (" + fact["unavailable_reason"] + ")"
        elif fact["value"] is None:
            val = none
        lines.append(f"- {fact['labels'][1 if language == 'en' else 0]}: {val} [{fact['evidence_id']}]")
    lines.append("\n### " + labels["interpretation"])
    facts = {f["fact_id"]: f for f in draft["facts"]}
    for claim in draft["interpretations"]:
        refs = list(dict.fromkeys([facts[f]["evidence_id"] for f in claim["fact_ids"]] + claim["chunk_ids"]))
        lines.append("- " + claim["text"] + " " + "".join(f"[{ref}]" for ref in refs))
    if not draft["interpretations"]:
        lines.append("- " + text("\u65e0\u901a\u8fc7\u590d\u6838\u7684\u89e3\u8bfb\uff0c\u4ec5\u63d0\u4ea4\u8bc1\u636e\u7f3a\u53e3\u3002", "No reviewed interpretation; evidence gaps only."))
    lines.append("\n### " + labels["gaps"])
    lines += ["- " + i for i in draft["unresolved_questions"] + draft["evidence_gaps"] + draft["proposed_next_steps"]] or ["- " + none]
    lines.append("\n### " + labels["checks"])
    for name, observation in draft["completed_checks"].items():
        lines.append(f"- {name}: {observation['status']} [{observation.get('evidence_id', 'no evidence ID')}]")
    lines += ["- " + c["chunk_id"] for c in draft["knowledge_references"]]
    lines.append(text("\u9644\u4ef6\uff1a\u65e0\u3002\u539f\u59cb\u68c0\u67e5\u6570\u636e\u4e0e\u5b8c\u6574\u5b57\u6bb5\u4fdd\u5b58\u5728\u8349\u7a3f JSON \u5185\u3002\u5de5\u5355\u72b6\u6001\u4ee5\u5de5\u4f5c\u6d41\u7684\u521b\u5efa\u56de\u6267\u4e3a\u51c6\uff1b\u4e0d\u53d1\u9001\u5916\u90e8\u7cfb\u7edf\u3002",
        "Attachments: none. Raw checks and full fields are in the draft JSON. Ticket creation is determined by the workflow receipt; nothing is sent externally."))
    return "\n".join(lines)
