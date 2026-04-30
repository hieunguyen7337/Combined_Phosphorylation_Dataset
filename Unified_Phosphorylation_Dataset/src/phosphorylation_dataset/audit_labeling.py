"""Utilities for expert audit labels on candidate phosphorylation relations."""

from __future__ import annotations

import html
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .io_utils import load_jsonl, write_jsonl


VALID_STATUSES = ("approved", "rejected", "needs_change")
VALID_PPI_LABELS = ("phosphorylation", "interaction", "no_relation", "uncertain")
ENTITY_ROLES = ("substrate", "kinase", "interactant", "protein", "unknown")


@dataclass(frozen=True)
class ConfirmedEntity:
    """One reviewer-confirmed entity span."""

    text: str
    start: int
    end: int
    role: str

    @classmethod
    def from_mapping(cls, value: dict) -> "ConfirmedEntity":
        return cls(
            text=str(value.get("text", "")),
            start=int(value.get("start", 0)),
            end=int(value.get("end", 0)),
            role=str(value.get("role", "unknown")),
        )

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "role": self.role,
        }


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def candidate_id(candidate: dict) -> str:
    """Return the stable id used to link a candidate to expert decisions."""
    value = candidate.get("candidate_id") or candidate.get("id")
    if not value:
        raise ValueError("Candidate record is missing both 'candidate_id' and 'id'.")
    return str(value)


def load_records(path: Path) -> list[dict]:
    """Load JSONL or JSON-array records from a path."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if text.startswith("["):
        records = json.loads(text)
        if not isinstance(records, list):
            raise ValueError(f"Expected a JSON array in {path}.")
        return records
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def append_jsonl(path: Path, record: dict) -> None:
    """Append one JSON object to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_decision(
    *,
    candidate_id_value: str,
    reviewer: str,
    status: str,
    ppi_label: str,
    confirmed_entity_1: ConfirmedEntity,
    confirmed_entity_2: ConfirmedEntity,
    confirmed_site: str,
    notes: str = "",
    supersedes_decision_id: str | None = None,
) -> dict:
    """Build one append-only expert decision record."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if ppi_label not in VALID_PPI_LABELS:
        raise ValueError(f"Invalid ppi_label: {ppi_label}")
    if not reviewer.strip():
        raise ValueError("Reviewer is required.")

    return {
        "candidate_id": candidate_id_value,
        "decision_id": str(uuid.uuid4()),
        "timestamp": utc_timestamp(),
        "reviewer": reviewer.strip(),
        "status": status,
        "ppi_label": ppi_label,
        "confirmed_entity_1": confirmed_entity_1.as_dict(),
        "confirmed_entity_2": confirmed_entity_2.as_dict(),
        "confirmed_site": confirmed_site,
        "notes": notes,
        "supersedes_decision_id": supersedes_decision_id,
    }


def latest_decisions(decisions: Iterable[dict]) -> dict[str, dict]:
    """Return the latest non-superseded decision for each candidate."""
    by_candidate: dict[str, list[dict]] = {}
    superseded: set[str] = set()

    for decision in decisions:
        decision_id = str(decision.get("decision_id", ""))
        supersedes = decision.get("supersedes_decision_id")
        if supersedes:
            superseded.add(str(supersedes))
        if decision_id:
            by_candidate.setdefault(str(decision.get("candidate_id", "")), []).append(decision)

    latest: dict[str, dict] = {}
    for cid, candidate_decisions in by_candidate.items():
        active = [
            decision
            for decision in candidate_decisions
            if str(decision.get("decision_id", "")) not in superseded
        ]
        if not active:
            continue
        latest[cid] = sorted(active, key=lambda item: str(item.get("timestamp", "")))[-1]
    return latest


def write_latest_decisions(decisions_path: Path, latest_path: Path) -> list[dict]:
    """Write latest decisions as a JSON array and return them."""
    decisions = load_records(decisions_path)
    latest = list(latest_decisions(decisions).values())
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest


def validate_entity_span(text: str, entity: ConfirmedEntity) -> None:
    """Ensure an entity span is valid and points to the declared text."""
    if entity.role not in ENTITY_ROLES:
        raise ValueError(f"Invalid entity role: {entity.role}")
    if entity.start < 0 or entity.end > len(text) or entity.start >= entity.end:
        raise ValueError(f"Invalid entity span: {entity.as_dict()}")
    actual = text[entity.start : entity.end]
    if actual != entity.text:
        raise ValueError(
            f"Entity span mismatch for {entity.as_dict()}: found {actual!r} in source text."
        )


def insert_markers_from_entities(
    text: str,
    first_entity: ConfirmedEntity,
    second_entity: ConfirmedEntity,
) -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Insert [E1]/[E2] in textual order and return marker-relative spans."""
    validate_entity_span(text, first_entity)
    validate_entity_span(text, second_entity)
    if first_entity.start > second_entity.start:
        first_entity, second_entity = second_entity, first_entity
    if first_entity.end > second_entity.start:
        raise ValueError("Confirmed entity spans overlap.")

    prefix = text[: first_entity.start]
    first_text = text[first_entity.start : first_entity.end]
    middle = text[first_entity.end : second_entity.start]
    second_text = text[second_entity.start : second_entity.end]
    suffix = text[second_entity.end :]
    marked_text = f"{prefix}[E1]{first_text}[/E1]{middle}[E2]{second_text}[/E2]{suffix}"

    first_marked_start = len(prefix) + len("[E1]")
    first_marked_end = first_marked_start + len(first_text)
    second_marked_start = (
        len(prefix)
        + len("[E1]")
        + len(first_text)
        + len("[/E1]")
        + len(middle)
        + len("[E2]")
    )
    second_marked_end = second_marked_start + len(second_text)
    return marked_text, (first_marked_start, first_marked_end), (second_marked_start, second_marked_end)


def build_approved_relation_record(candidate: dict, decision: dict) -> dict:
    """Build one unified JSONL record from an approved expert decision."""
    text = str(candidate.get("text", ""))
    entity_1 = ConfirmedEntity.from_mapping(decision["confirmed_entity_1"])
    entity_2 = ConfirmedEntity.from_mapping(decision["confirmed_entity_2"])
    marked_text, first_marked_span, second_marked_span = insert_markers_from_entities(
        text,
        entity_1,
        entity_2,
    )

    first_entity = entity_1
    second_entity = entity_2
    if entity_1.start > entity_2.start:
        first_entity = entity_2
        second_entity = entity_1

    kinase = entity_1.text if entity_1.role == "kinase" else entity_2.text if entity_2.role == "kinase" else ""
    substrate = (
        entity_1.text
        if entity_1.role == "substrate"
        else entity_2.text
        if entity_2.role == "substrate"
        else ""
    )

    record = dict(candidate)
    record.update(
        {
            "id": f"{candidate_id(candidate)}_{decision['decision_id']}",
            "text": text,
            "text_with_entity_marker": marked_text,
            "relation": [
                {
                    "PPI_relation_type": decision["ppi_label"],
                    "relation_id": 0,
                    "entity_1": first_entity.text,
                    "entity_1_idx": [[first_entity.start, first_entity.end]],
                    "entity_1_idx_in_text_with_entity_marker": [
                        first_marked_span[0],
                        first_marked_span[1],
                    ],
                    "entity_1_type": "protein",
                    "entity_1_type_id": 0,
                    "entity_2": second_entity.text,
                    "entity_2_idx": [[second_entity.start, second_entity.end]],
                    "entity_2_idx_in_text_with_entity_marker": [
                        second_marked_span[0],
                        second_marked_span[1],
                    ],
                    "entity_2_type": "protein",
                    "entity_2_type_id": 0,
                }
            ],
            "Kinase": kinase or candidate.get("Kinase", ""),
            "Substrate": substrate or candidate.get("Substrate", ""),
            "Site": decision.get("confirmed_site") or candidate.get("Site", ""),
            "PPI": decision["ppi_label"],
            "Interactant": kinase or candidate.get("Interactant", ""),
            "source": "rlims_p_v1",
            "requires_manual_audit": False,
            "audit_decision_id": decision["decision_id"],
            "audit_reviewer": decision["reviewer"],
            "audit_timestamp": decision["timestamp"],
        }
    )
    return record


def export_approved_records(candidates_path: Path, decisions_path: Path, output_path: Path) -> list[dict]:
    """Export approved phosphorylation decisions to unified JSONL records."""
    candidates = {candidate_id(record): record for record in load_records(candidates_path)}
    latest = latest_decisions(load_records(decisions_path))
    output_records: list[dict] = []

    for cid, decision in sorted(latest.items()):
        if decision.get("status") != "approved" or decision.get("ppi_label") != "phosphorylation":
            continue
        candidate = candidates.get(cid)
        if candidate is None:
            raise ValueError(f"Approved decision references missing candidate: {cid}")
        output_records.append(build_approved_relation_record(candidate, decision))

    write_jsonl(output_path, output_records)
    return output_records


def default_entity_from_relation(candidate: dict, index: int) -> ConfirmedEntity:
    """Extract an editable default entity from a candidate relation."""
    relation = (candidate.get("relation") or [{}])[0]
    prefix = f"entity_{index}"
    idx = relation.get(f"{prefix}_idx") or [[0, 0]]
    start, end = idx[0]
    text = str(relation.get(prefix, ""))
    role = "unknown"
    if text and text == str(candidate.get("Kinase", "")):
        role = "kinase"
    elif text and text == str(candidate.get("Substrate", "")):
        role = "substrate"
    return ConfirmedEntity(text=text, start=int(start), end=int(end), role=role)


def highlighted_text_html(text: str, spans: list[tuple[int, int, str]]) -> str:
    """Render source text with simple span highlighting."""
    valid_spans = sorted(
        [(start, end, label) for start, end, label in spans if 0 <= start < end <= len(text)],
        key=lambda item: (item[0], item[1]),
    )
    chunks: list[str] = []
    cursor = 0
    for start, end, label in valid_spans:
        if start < cursor:
            continue
        chunks.append(html.escape(text[cursor:start]))
        chunks.append(f'<mark class="{html.escape(label)}">{html.escape(text[start:end])}</mark>')
        cursor = end
    chunks.append(html.escape(text[cursor:]))
    rendered = "".join(chunks)
    rendered = re.sub(
        r"(\bphosphorylat\w*|\bphospho\w*)",
        r'<span class="trigger">\1</span>',
        rendered,
        flags=re.IGNORECASE,
    )
    return rendered
