"""Versioned local Chroma index over current Demo Bench knowledge only."""

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX_VERSION = "sections-700-v1-minilm"


def load_chunks(knowledge_root: Path, applies_to: str = "demo-bench-v1") -> list[dict]:
    chunks, seen = [], set()
    for path in sorted(knowledge_root.glob("*/*.md")):
        if path.parent.name == "archived":
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"Missing knowledge metadata: {path.name}")
        _, header, body = text.split("---", 2)
        meta = yaml.safe_load(header)
        for key in ("doc_id", "title", "version", "status", "source_type", "applies_to", "source_ids"):
            if key not in meta:
                raise ValueError(f"Missing {key}: {path.name}")
        if meta["status"] != "current" or applies_to not in meta["applies_to"]:
            continue
        if meta["doc_id"] in seen:
            raise ValueError("Duplicate knowledge document ID.")
        seen.add(meta["doc_id"])
        sections = re.split(r"(?m)^## ", body.strip())
        number = 0
        for section in sections:
            heading, _, content = section.partition("\n")
            content = content.strip()
            if not content:
                continue
            # Limit text per embedding to avoid silently truncating long sections.
            words = content.split()
            parts, current = [], []
            for word in words:
                if current and len(" ".join(current + [word])) > 700:
                    parts.append(" ".join(current))
                    current = []
                current.append(word)
            if current:
                parts.append(" ".join(current))
            for part in parts:
                number += 1
                metadata = {"doc_id": meta["doc_id"], "title": meta["title"],
                            "version": str(meta["version"]), "status": meta["status"],
                            "source_type": meta["source_type"], "applies_to": applies_to,
                            "source_ids": json.dumps(meta["source_ids"]),
                            "section": heading.lstrip("# "),
                            "knowledge_path": path.relative_to(knowledge_root).as_posix()}
                chunks.append({"id": f"{meta['doc_id']}::c{number:02d}", "metadata": metadata,
                               "text": f"{meta['title']}\n{heading.lstrip('# ')}\n{part}"})
    if not chunks:
        raise ValueError("No current Demo Bench knowledge documents found.")
    return chunks


class KnowledgeIndex:
    def __init__(self, knowledge_root: Path | None = None, index_root: Path | None = None,
                 applies_to: str = "demo-bench-v1"):
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        chunks = load_chunks(knowledge_root or ROOT / "knowledge", applies_to=applies_to)
        fingerprint = hashlib.sha256((INDEX_VERSION + json.dumps(chunks, sort_keys=True)).encode()).hexdigest()
        self.knowledge_version = fingerprint[:16]
        self._client = chromadb.PersistentClient(
            path=str(index_root or ROOT / "data" / "index"),
            settings=Settings(anonymized_telemetry=False),
        )
        embedding = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
        embedding.DOWNLOAD_PATH = ROOT / "data" / "models" / embedding.MODEL_NAME
        self._collection = self._client.get_or_create_collection(
            name="bench-" + self.knowledge_version, embedding_function=embedding,
            metadata={"hnsw:space": "cosine", "knowledge_version": self.knowledge_version},
        )
        # The content-derived collection is reusable; upsert repairs interrupted builds.
        if self._collection.count() != len(chunks):
            self._collection.upsert(ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks],
                                    metadatas=[c["metadata"] for c in chunks])
        self.chunk_count = len(chunks)

    def search(self, query: str, top_k: int = 4) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            return {"status": "error", "error": {"code": "INVALID_QUERY", "message": "Use a nonempty English query up to 1000 characters."}}
        if type(top_k) is not int or not 1 <= top_k <= 5:
            return {"status": "error", "error": {"code": "INVALID_TOP_K", "message": "top_k must be 1 to 5."}}
        result = self._collection.query(query_texts=[query.strip()], n_results=min(top_k, self.chunk_count))
        matches = []
        for chunk_id, text, meta, distance in zip(result["ids"][0], result["documents"][0],
                                                 result["metadatas"][0], result["distances"][0]):
            matches.append({"chunk_id": chunk_id, **meta, "source_ids": json.loads(meta["source_ids"]),
                            "text": text, "cosine_distance": distance})
        return {"status": "ok", "knowledge_version": self.knowledge_version,
                "matches": matches, "note": "Similarity ranks candidates; it does not establish applicability or truth."}


SEARCH_TOOL = {"name": "search_knowledge", "description":
    "Search current English Demo Bench documents for applicable rules. Use focused English queries, even for a Chinese user question. Cite returned chunk_id values.",
    "input_schema": {"type": "object", "properties": {
        "query": {"type": "string", "minLength": 1, "maxLength": 1000},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 5, "default": 4}},
        "required": ["query"], "additionalProperties": False}}
