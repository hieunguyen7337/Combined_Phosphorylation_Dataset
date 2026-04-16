"""Verification helpers for the combined phosphorylation dataset."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .io_utils import load_jsonl


def build_verification_report(file_path: Path) -> str:
    """Return a markdown verification report for the combined dataset."""
    records = load_jsonl(file_path)
    total_entries = len(records)
    marked_texts = [record.get("text_with_entity_marker", "") for record in records]
    unique_marked_texts = set(marked_texts)
    all_sources = sorted({record.get("source", "Unknown") for record in records})

    lines: list[str] = []
    lines.append("# Final Dataset Verification")
    lines.append("")
    lines.append(f"- File: `{file_path}`")
    lines.append(f"- Total entries: **{total_entries:,}**")
    lines.append(f"- Unique `text_with_entity_marker`: **{len(unique_marked_texts):,}**")
    lines.append(
        "- Marker uniqueness check: **PASS**"
        if len(unique_marked_texts) == total_entries
        else f"- Marker uniqueness check: **FAIL** ({total_entries - len(unique_marked_texts):,} duplicates)"
    )
    lines.append("")
    lines.append("## Source Statistics & Relations")
    lines.append("")
    lines.append("| Source | Total | Text Unique | Text Duplicates | Relation Types (All) |")
    lines.append("| --- | --- | --- | --- | --- |")

    source_stats: dict[str, dict] = {}
    for source_name in all_sources:
        source_records = [record for record in records if record.get("source") == source_name]
        raw_texts = [record.get("text", "") for record in source_records]
        relation_types: Counter = Counter()
        for record in source_records:
            relations = record.get("relation", [])
            if relations:
                for relation in relations:
                    relation_types[relation.get("PPI_relation_type", "Unknown")] += 1
            else:
                relation_types["None"] += 1

        source_stats[source_name] = {
            "total": len(source_records),
            "text_unique": len(set(raw_texts)),
            "text_duplicates": len(source_records) - len(set(raw_texts)),
            "relation_types": relation_types,
        }

    for source_name in all_sources:
        stats = source_stats[source_name]
        relation_text = ", ".join(f"{name}: {count}" for name, count in stats["relation_types"].most_common())
        lines.append(
            f"| **{source_name}** | {stats['total']:,} | {stats['text_unique']:,} | "
            f"{stats['text_duplicates']:,} | {relation_text} |"
        )

    global_relation_types: Counter = Counter()
    for stats in source_stats.values():
        global_relation_types.update(stats["relation_types"])

    unique_raw_texts = len({record.get("text", "") for record in records})
    lines.append(
        f"| **OVERALL** | **{total_entries:,}** | **{unique_raw_texts:,}** | "
        f"**{total_entries - unique_raw_texts:,}** | "
        f"{', '.join(f'{name}: {count}' for name, count in global_relation_types.most_common())} |"
    )
    lines.append("")
    return "\n".join(lines)
