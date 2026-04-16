"""Convert RLIMS-P v2 BRAT annotations into the unified JSONL schema."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .io_utils import write_jsonl


@dataclass(frozen=True)
class Entity:
    """A BRAT entity annotation."""

    entity_id: str
    entity_type: str
    spans: list[tuple[int, int]]
    text: str


@dataclass(frozen=True)
class Event:
    """A BRAT event annotation."""

    event_id: str
    event_type: str
    trigger: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class ConversionStats:
    """Summary counts for a conversion run."""

    total_events: int = 0
    kept: int = 0
    dropped: int = 0

    def add(self, other: "ConversionStats") -> "ConversionStats":
        return ConversionStats(
            total_events=self.total_events + other.total_events,
            kept=self.kept + other.kept,
            dropped=self.dropped + other.dropped,
        )


@dataclass(frozen=True)
class ConversionResult:
    """Rows plus the stats describing how they were produced."""

    rows: list[dict]
    stats_by_split: dict[str, ConversionStats]
    aggregate: ConversionStats


def parse_ann(path: Path) -> tuple[dict[str, Entity], list[Event]]:
    """Parse BRAT .ann files into entity and event structures."""
    entities: dict[str, Entity] = {}
    events: list[Event] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue

        if line.startswith("T"):
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            entity_id = parts[0]
            type_and_spans = parts[1]
            mention_text = parts[2]
            tokens = type_and_spans.split()
            if not tokens:
                continue

            entity_type = tokens[0]
            span_string = " ".join(tokens[1:])
            spans: list[tuple[int, int]] = []
            for segment in span_string.split(";"):
                match = re.match(r"^(\d+)\s+(\d+)$", segment.strip())
                if match:
                    spans.append((int(match.group(1)), int(match.group(2))))

            if spans:
                entities[entity_id] = Entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    spans=spans,
                    text=mention_text,
                )

        elif line.startswith("E"):
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            event_id = parts[0]
            pieces = parts[1].split()
            if not pieces or ":" not in pieces[0]:
                continue

            event_type, trigger = pieces[0].split(":", 1)
            arguments: dict[str, str] = {}
            for piece in pieces[1:]:
                if ":" not in piece:
                    continue
                role, reference = piece.split(":", 1)
                arguments[role] = reference

            events.append(
                Event(
                    event_id=event_id,
                    event_type=event_type,
                    trigger=trigger,
                    arguments=arguments,
                )
            )

    return entities, events


def extract_entity_text(entity: Entity, text: str) -> str | None:
    """Return entity text extracted from spans or None if spans are invalid."""
    chunks: list[str] = []
    for start, end in entity.spans:
        if start < 0 or end > len(text) or start >= end:
            return None
        chunks.append(text[start:end])
    return " ".join(chunks)


def insert_markers(
    text: str,
    first_span: tuple[int, int],
    second_span: tuple[int, int],
) -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Insert [E1]/[E2] markers and return marker-relative spans."""
    first_start, first_end = first_span
    second_start, second_end = second_span

    if first_start > second_start:
        raise ValueError("Marker insertion expects entities in textual order.")
    if first_end > second_start:
        raise ValueError("Overlapping entities are not supported.")

    prefix = text[:first_start]
    first_text = text[first_start:first_end]
    middle = text[first_end:second_start]
    second_text = text[second_start:second_end]
    suffix = text[second_end:]

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


def convert_split(root: Path, curator: str, split: str) -> tuple[list[dict], ConversionStats]:
    """Convert one curator/split pair from BRAT to JSONL records."""
    annotation_dir = root / curator / "brat" / split
    text_files = sorted(annotation_dir.glob("*.txt"))

    rows: list[dict] = []
    total_events = 0
    kept = 0
    dropped = 0

    for text_path in text_files:
        ann_path = text_path.with_suffix(".ann")
        if not ann_path.exists():
            continue

        text = text_path.read_text(encoding="utf-8")
        entities, events = parse_ann(ann_path)

        for event in events:
            if event.event_type != "Phosphorylation":
                continue

            total_events += 1
            theme_id = event.arguments.get("Theme")
            cause_id = event.arguments.get("Cause")
            if not theme_id or not cause_id:
                dropped += 1
                continue

            theme_entity = entities.get(theme_id)
            cause_entity = entities.get(cause_id)
            if not theme_entity or not cause_entity:
                dropped += 1
                continue

            if theme_entity.entity_type != "Protein" or cause_entity.entity_type != "Protein":
                dropped += 1
                continue

            theme_text = extract_entity_text(theme_entity, text)
            cause_text = extract_entity_text(cause_entity, text)
            if theme_text is None or cause_text is None:
                dropped += 1
                continue

            theme_span = theme_entity.spans[0]
            cause_span = cause_entity.spans[0]
            substrate = theme_text
            interactant = cause_text

            if theme_span[0] <= cause_span[0]:
                first_name, first_span = substrate, theme_span
                second_name, second_span = interactant, cause_span
            else:
                first_name, first_span = interactant, cause_span
                second_name, second_span = substrate, theme_span

            if text[first_span[0]:first_span[1]] != first_name or text[second_span[0]:second_span[1]] != second_name:
                dropped += 1
                continue

            try:
                marked_text, first_marked_span, second_marked_span = insert_markers(
                    text,
                    first_span,
                    second_span,
                )
            except ValueError:
                dropped += 1
                continue

            record_id = f"{curator}_{split}_{text_path.stem}_{event.event_id}"
            row = {
                "id": record_id,
                "text": text,
                "text_with_entity_marker": marked_text,
                "relation": [
                    {
                        "PPI_relation_type": "interaction",
                        "relation_id": 0,
                        "entity_1": first_name,
                        "entity_1_idx": [[first_span[0], first_span[1]]],
                        "entity_1_idx_in_text_with_entity_marker": [
                            first_marked_span[0],
                            first_marked_span[1],
                        ],
                        "entity_1_type": "protein",
                        "entity_1_type_id": 0,
                        "entity_2": second_name,
                        "entity_2_idx": [[second_span[0], second_span[1]]],
                        "entity_2_idx_in_text_with_entity_marker": [
                            second_marked_span[0],
                            second_marked_span[1],
                        ],
                        "entity_2_type": "protein",
                        "entity_2_type_id": 0,
                    }
                ],
                "PMC ID": "",
                "Subsec ID": "",
                "Subsec Type": "",
                "Kinase": cause_entity.text,
                "Substrate": theme_entity.text,
                "Site": entities[event.arguments["Site"]].text
                if "Site" in event.arguments and event.arguments["Site"] in entities
                else "",
                "Impact": "",
                "PPI": "interaction",
                "Interactant": cause_entity.text,
                "SentIDs": "",
            }
            rows.append(row)
            kept += 1

    return rows, ConversionStats(total_events=total_events, kept=kept, dropped=dropped)


def convert_dataset(
    root: Path,
    curators: list[str],
    splits: list[str],
    output_path: Path,
) -> ConversionResult:
    """Convert all requested RLIMS-P folders and write the JSONL output."""
    all_rows: list[dict] = []
    stats_by_split: dict[str, ConversionStats] = {}
    aggregate = ConversionStats()

    for curator in curators:
        for split in splits:
            rows, stats = convert_split(root, curator, split)
            key = f"{curator}/{split}"
            stats_by_split[key] = stats
            all_rows.extend(rows)
            aggregate = aggregate.add(stats)

    write_jsonl(output_path, all_rows)
    return ConversionResult(rows=all_rows, stats_by_split=stats_by_split, aggregate=aggregate)
