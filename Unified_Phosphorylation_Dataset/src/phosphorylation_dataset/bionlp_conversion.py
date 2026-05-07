"""Prepare BioNLP Shared Task phosphorylation events for manual audit."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .io_utils import write_jsonl
from .rlims_conversion import insert_markers


PHOSPHO_EVENT_TYPES = {"Phosphorylation", "Dephosphorylation"}


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: str
    spans: list[tuple[int, int]]
    text: str


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    trigger: str
    arguments: dict[str, list[str]]


@dataclass(frozen=True)
class SourceSpec:
    name: str
    root: Path


@dataclass(frozen=True)
class SourceStats:
    documents: int = 0
    raw_events: int = 0
    audit_candidates: int = 0
    explicit_cause_candidates: int = 0
    rejected: int = 0


@dataclass(frozen=True)
class BionlpAuditResult:
    raw_records: list[dict]
    audit_candidates: list[dict]
    rejected_records: list[dict]
    stats_by_source: dict[str, SourceStats]
    report_markdown: str


def parse_standoff(path: Path) -> tuple[dict[str, Entity], dict[str, Event]]:
    """Parse text-bound and event annotations from one BioNLP standoff file."""
    entities: dict[str, Entity] = {}
    events: dict[str, Event] = {}
    if not path.exists():
        return entities, events

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue

        if line.startswith("T"):
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            tokens = parts[1].split()
            if not tokens:
                continue

            spans: list[tuple[int, int]] = []
            for segment in " ".join(tokens[1:]).split(";"):
                match = re.match(r"^(\d+)\s+(\d+)$", segment.strip())
                if match:
                    spans.append((int(match.group(1)), int(match.group(2))))

            if spans:
                entities[parts[0]] = Entity(parts[0], tokens[0], spans, parts[2])

        elif line.startswith("E"):
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            pieces = parts[1].split()
            if not pieces or ":" not in pieces[0]:
                continue

            event_type, trigger = pieces[0].split(":", 1)
            arguments: dict[str, list[str]] = defaultdict(list)
            for piece in pieces[1:]:
                if ":" not in piece:
                    continue
                role, reference = piece.split(":", 1)
                arguments[re.sub(r"\d+$", "", role)].append(reference)

            events[parts[0]] = Event(parts[0], event_type, trigger, dict(arguments))

    return entities, events


def entity_to_dict(entity: Entity | None) -> dict | None:
    if entity is None:
        return None
    return {
        "id": entity.entity_id,
        "type": entity.entity_type,
        "text": entity.text,
        "spans": entity.spans,
    }


def document_id_fields(document_id: str) -> dict:
    return {
        "PMID": document_id.removeprefix("PMID-") if document_id.startswith("PMID-") else "",
        "PMC ID": document_id if document_id.startswith("PMC") else "",
    }


def read_document(text_path: Path) -> tuple[str, dict[str, Entity], dict[str, Event]]:
    text = text_path.read_text(encoding="utf-8")
    a1_entities, a1_events = parse_standoff(text_path.with_suffix(".a1"))
    a2_entities, a2_events = parse_standoff(text_path.with_suffix(".a2"))
    return text, {**a1_entities, **a2_entities}, {**a1_events, **a2_events}


def first_argument_entity(
    event: Event,
    role: str,
    entities: dict[str, Entity],
    allowed_types: set[str] | None = None,
) -> Entity | None:
    for entity_id in event.arguments.get(role, []):
        entity = entities.get(entity_id)
        if entity and (allowed_types is None or entity.entity_type in allowed_types):
            return entity
    return None


def find_explicit_cause(event: Event, entities: dict[str, Entity], events: dict[str, Event]) -> Entity | None:
    """Resolve direct BioNLP Cause or EPI Catalysis Cause as audit evidence only."""
    direct = first_argument_entity(event, "Cause", entities, {"Protein"})
    if direct is not None:
        return direct

    for candidate in events.values():
        if candidate.event_type != "Catalysis":
            continue
        if event.event_id not in candidate.arguments.get("Theme", []):
            continue
        cause = first_argument_entity(candidate, "Cause", entities, {"Protein"})
        if cause is not None:
            return cause

    return None


def make_raw_record(
    source_name: str,
    source_root: Path,
    text_path: Path,
    text: str,
    event: Event,
    trigger: Entity | None,
    theme: Entity | None,
    site: Entity | None,
    cause: Entity | None,
) -> dict:
    document_id = text_path.stem
    record = {
        "id": f"{source_name}_{document_id}_{event.event_id}",
        "source": "bionlp",
        "source_corpus": source_name,
        "source_path": str(text_path.relative_to(source_root)),
        "document_id": document_id,
        "text": text,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_arguments": event.arguments,
        "event_trigger": entity_to_dict(trigger),
        "substrate": entity_to_dict(theme),
        "site": entity_to_dict(site),
        "annotated_cause": entity_to_dict(cause),
        "requires_manual_audit": True,
        "audit_status": "unreviewed",
    }
    record.update(document_id_fields(document_id))
    return record


def make_audit_candidate(raw: dict) -> dict | None:
    trigger = raw.get("event_trigger")
    substrate = raw.get("substrate")
    if not trigger or not substrate:
        return None

    trigger_span = tuple(trigger["spans"][0])
    substrate_span = tuple(substrate["spans"][0])
    if trigger_span[0] <= substrate_span[0]:
        first_span, second_span = trigger_span, substrate_span
        first_label, second_label = "event_trigger", "substrate"
    else:
        first_span, second_span = substrate_span, trigger_span
        first_label, second_label = "substrate", "event_trigger"

    try:
        marked, first_marked, second_marked = insert_markers(raw["text"], first_span, second_span)
    except ValueError:
        return None

    marked_spans = {
        first_label: [first_marked[0], first_marked[1]],
        second_label: [second_marked[0], second_marked[1]],
    }
    candidate = {
        "id": f"{raw['id']}_AUDIT",
        "candidate_id": f"{raw['id']}_AUDIT",
        "source_record_id": raw["id"],
        "source": "bionlp",
        "source_corpus": raw["source_corpus"],
        "document_id": raw["document_id"],
        "PMID": raw.get("PMID", ""),
        "PMC ID": raw.get("PMC ID", ""),
        "text": raw["text"],
        "text_with_entity_marker": marked,
        "relation": [],
        "event_type": raw["event_type"],
        "event_trigger": trigger,
        "substrate": substrate,
        "site": raw.get("site"),
        "annotated_cause": raw.get("annotated_cause"),
        "marker_semantics": {
            "E1": first_label,
            "E2": second_label,
            "marked_spans": marked_spans,
        },
        "candidate_task": "manual_phosphorylation_relation_annotation",
        "candidate_note": "BioNLP provides event evidence. Kinase-substrate/PPI labels must be manually audited before training export.",
        "requires_manual_audit": True,
        "audit_status": "unreviewed",
    }
    return candidate


def write_brat_record(output_dir: Path, candidate: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / candidate["id"]
    text = candidate["text"]
    base.with_suffix(".txt").write_text(text, encoding="utf-8")

    lines: list[str] = []
    tid = 1
    for label, entity in (
        ("Trigger", candidate.get("event_trigger")),
        ("Substrate", candidate.get("substrate")),
        ("Site", candidate.get("site")),
        ("AnnotatedCause", candidate.get("annotated_cause")),
    ):
        if not entity:
            continue
        for start, end in entity.get("spans", []):
            lines.append(f"T{tid}\t{label} {start} {end}\t{text[start:end]}")
            tid += 1

    base.with_suffix(".ann").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def convert_source(source: SourceSpec) -> tuple[list[dict], list[dict], list[dict], SourceStats]:
    raw_records: list[dict] = []
    audit_candidates: list[dict] = []
    rejected_records: list[dict] = []
    documents = raw_events = explicit_cause_candidates = rejected = 0

    for text_path in sorted(source.root.rglob("*.txt")):
        if not text_path.with_suffix(".a2").exists():
            continue

        documents += 1
        text, entities, events = read_document(text_path)
        for event in events.values():
            if event.event_type not in PHOSPHO_EVENT_TYPES:
                continue

            raw_events += 1
            trigger = entities.get(event.trigger)
            theme = first_argument_entity(event, "Theme", entities, {"Protein"})
            site = first_argument_entity(event, "Site", entities)
            cause = find_explicit_cause(event, entities, events)
            raw = make_raw_record(source.name, source.root, text_path, text, event, trigger, theme, site, cause)
            raw_records.append(raw)

            candidate = make_audit_candidate(raw)
            if candidate is None:
                rejected_record = dict(raw)
                rejected_record["rejection_reason"] = "missing_or_overlapping_trigger_substrate_marker_pair"
                rejected_records.append(rejected_record)
                rejected += 1
                continue

            audit_candidates.append(candidate)
            if cause is not None:
                explicit_cause_candidates += 1

    stats = SourceStats(
        documents=documents,
        raw_events=raw_events,
        audit_candidates=len(audit_candidates),
        explicit_cause_candidates=explicit_cause_candidates,
        rejected=rejected,
    )
    return raw_records, audit_candidates, rejected_records, stats


def build_report(raw: list[dict], candidates: list[dict], rejected: list[dict], stats_by_source: dict[str, SourceStats]) -> str:
    event_types = Counter(record.get("event_type", "") for record in raw)
    sources = Counter(record.get("source_corpus", "") for record in raw)
    cause_count = sum(1 for record in candidates if record.get("annotated_cause"))
    lines = [
        "# BioNLP Manual Audit Candidate Conversion",
        "",
        f"Raw phosphorylation/dephosphorylation events: {len(raw)}",
        f"Audit candidates: {len(candidates)}",
        f"Candidates with explicit BioNLP Cause/Catalysis evidence: {cause_count}",
        f"Rejected events: {len(rejected)}",
        "",
        "These records are not a ready PPI training dataset. Every candidate requires manual kinase-substrate/PPI annotation before export.",
        "",
        "## Source Counts",
        "",
    ]
    for source, count in sources.most_common():
        stats = stats_by_source[source]
        lines.append(
            f"- {source}: raw_events={count}, audit_candidates={stats.audit_candidates}, "
            f"explicit_cause_candidates={stats.explicit_cause_candidates}, rejected={stats.rejected}"
        )
    lines.extend(["", "## Event Types", ""])
    for event_type, count in event_types.most_common():
        lines.append(f"- {event_type}: {count}")
    if rejected:
        lines.extend(["", "## Rejection Reasons", ""])
        for reason, count in Counter(record.get("rejection_reason", "") for record in rejected).most_common():
            lines.append(f"- {reason}: {count}")
    return "\n".join(lines)


def convert_bionlp_for_audit(
    *,
    sources: list[SourceSpec],
    raw_output: Path,
    candidate_output: Path,
    rejected_output: Path,
    report_path: Path,
    brat_output: Path | None = None,
) -> BionlpAuditResult:
    if brat_output is not None and brat_output.exists():
        for stale_file in list(brat_output.glob("*.ann")) + list(brat_output.glob("*.txt")):
            stale_file.unlink()

    all_raw: list[dict] = []
    all_candidates: list[dict] = []
    all_rejected: list[dict] = []
    stats_by_source: dict[str, SourceStats] = {}

    for source in sources:
        raw, candidates, rejected, stats = convert_source(source)
        all_raw.extend(raw)
        all_candidates.extend(candidates)
        all_rejected.extend(rejected)
        stats_by_source[source.name] = stats

    if brat_output is not None:
        for candidate in all_candidates:
            write_brat_record(brat_output, candidate)

    report = build_report(all_raw, all_candidates, all_rejected, stats_by_source)
    write_jsonl(raw_output, all_raw)
    write_jsonl(candidate_output, all_candidates)
    write_jsonl(rejected_output, all_rejected)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    return BionlpAuditResult(
        raw_records=all_raw,
        audit_candidates=all_candidates,
        rejected_records=all_rejected,
        stats_by_source=stats_by_source,
        report_markdown=report,
    )
