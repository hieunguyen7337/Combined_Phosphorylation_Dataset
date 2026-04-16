"""Combine normalized phosphorylation datasets and produce analysis reports."""

from __future__ import annotations

import copy
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .io_utils import load_jsonl, write_jsonl


@dataclass(frozen=True)
class SourceSummary:
    """Per-source summary used in reporting."""

    total: int
    accepted: int
    duplicates: int
    relation_types: Counter
    word_counts: list[int]
    sentence_counts: list[int]


@dataclass(frozen=True)
class CombinedDatasetResult:
    """Combined records plus the generated markdown report."""

    records: list[dict]
    source_summaries: dict[str, SourceSummary]
    marker_patterns: Counter
    report_markdown: str


def count_words(text: str) -> int:
    return len(text.split())


def count_sentences(text: str) -> int:
    sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", text)
    return len([sentence for sentence in sentences if sentence.strip()])


def extract_marker_pattern(text_with_marker: str) -> str:
    markers = re.findall(r"\[/?E[\d\-]+.*?\]", text_with_marker)
    return " - ".join(markers)


def fix_marker_order(entry: dict) -> dict:
    """Ensure [E1] appears before [E2] in marked text and relation metadata."""
    text_with_marker = entry.get("text_with_entity_marker", "")
    e1_position = text_with_marker.find("[E1]")
    e2_position = text_with_marker.find("[E2]")

    if e2_position != -1 and e1_position != -1 and e2_position < e1_position:
        text_with_marker = text_with_marker.replace("[E1]", "TEMP_E1").replace("[/E1]", "TEMP_CLOSE_E1")
        text_with_marker = text_with_marker.replace("[E2]", "[E1]").replace("[/E2]", "[/E1]")
        text_with_marker = text_with_marker.replace("TEMP_E1", "[E2]").replace("TEMP_CLOSE_E1", "[/E2]")
        entry["text_with_entity_marker"] = text_with_marker

        new_relations = []
        for relation in entry.get("relation", []):
            new_relation = copy.deepcopy(relation)
            new_relation["entity_1"] = relation.get("entity_2")
            new_relation["entity_2"] = relation.get("entity_1")
            new_relation["entity_1_type"] = relation.get("entity_2_type")
            new_relation["entity_2_type"] = relation.get("entity_1_type")
            new_relation["entity_1_type_id"] = relation.get("entity_2_type_id")
            new_relation["entity_2_type_id"] = relation.get("entity_1_type_id")
            new_relation["entity_1_idx"] = relation.get("entity_2_idx")
            new_relation["entity_2_idx"] = relation.get("entity_1_idx")
            new_relation["entity_1_idx_in_text_with_entity_marker"] = relation.get(
                "entity_2_idx_in_text_with_entity_marker"
            )
            new_relation["entity_2_idx_in_text_with_entity_marker"] = relation.get(
                "entity_1_idx_in_text_with_entity_marker"
            )
            new_relations.append(new_relation)
        entry["relation"] = new_relations

    return entry


def build_analysis_report(
    records: list[dict],
    source_summaries: dict[str, SourceSummary],
    marker_patterns: Counter,
) -> str:
    """Render a markdown analysis report for the combined dataset."""
    lines: list[str] = []
    lines.append("# Dataset Analysis: Combined PPI")
    lines.append("")
    lines.append(f"**Total Unique Entries**: **{len(records):,}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Source Statistics & Relations")
    lines.append("")
    lines.append("High-level overview of each source after strict deduplication by `text_with_entity_marker`.")
    lines.append("")
    lines.append("| Source | Original Total | Accepted (Unique) | Duplicates Dropped | Top Relation Types |")
    lines.append("| --- | --- | --- | --- | --- |")

    for source_name, summary in source_summaries.items():
        top_relations = summary.relation_types.most_common(3)
        relation_text = ", ".join(f"{name}: {count}" for name, count in top_relations)
        if len(summary.relation_types) > 3:
            relation_text += ", ..."
        lines.append(
            f"| **{source_name}** | {summary.total:,} | {summary.accepted:,} | {summary.duplicates:,} | {relation_text} |"
        )

    lines.append("")
    lines.append("> **Note**: Deduplication is global and applied sequentially across the source files.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Entity Marker Patterns")
    lines.append("")
    lines.append("The pattern below shows the order in which marked entities appear inside `text_with_entity_marker`.")
    lines.append("")
    lines.append("| Pattern | Count | Sources |")
    lines.append("| --- | --- | --- |")

    for pattern, count in marker_patterns.most_common(10):
        contributing_sources = sorted(
            {
                record["source"]
                for record in records
                if extract_marker_pattern(record.get("text_with_entity_marker", "")) == pattern
            }
        )
        lines.append(f"| `{pattern}` | {count:,} | {', '.join(contributing_sources)} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Text & Linguistic Statistics")
    lines.append("")
    lines.append("Comparison of word counts and sentence counts for accepted entries only.")
    lines.append("")
    lines.append("| Source | Avg. Words | Range (Words) | Avg. Sents | Range (Sents) |")
    lines.append("| --- | --- | --- | --- | --- |")

    all_word_counts: list[int] = []
    all_sentence_counts: list[int] = []

    for source_name, summary in source_summaries.items():
        if summary.word_counts:
            avg_words = statistics.mean(summary.word_counts)
            avg_sentences = statistics.mean(summary.sentence_counts)
            all_word_counts.extend(summary.word_counts)
            all_sentence_counts.extend(summary.sentence_counts)
            lines.append(
                f"| **{source_name}** | {avg_words:.2f} | {min(summary.word_counts)} - {max(summary.word_counts)} | "
                f"{avg_sentences:.2f} | {min(summary.sentence_counts)} - {max(summary.sentence_counts)} |"
            )
        else:
            lines.append(f"| **{source_name}** | 0 | 0 - 0 | 0 | 0 - 0 |")

    if all_word_counts:
        lines.append(
            f"| **OVERALL** | **{statistics.mean(all_word_counts):.2f}** | "
            f"**{min(all_word_counts)} - {max(all_word_counts)}** | "
            f"**{statistics.mean(all_sentence_counts):.2f}** | "
            f"**{min(all_sentence_counts)} - {max(all_sentence_counts)}** |"
        )

    lines.append("")
    return "\n".join(lines)


def combine_datasets(files_map: dict[str, Path], output_path: Path) -> CombinedDatasetResult:
    """Combine normalized datasets, deduplicate them, and write the final JSONL output."""
    all_records: list[dict] = []
    source_summaries: dict[str, SourceSummary] = {}
    seen_marked_texts: set[str] = set()

    for source_name, file_path in files_map.items():
        entries = load_jsonl(file_path)
        total_entries = 0
        accepted_entries = 0
        duplicates = 0
        relation_types: Counter = Counter()
        word_counts: list[int] = []
        sentence_counts: list[int] = []
        accepted_records: list[dict] = []

        for entry in entries:
            total_entries += 1
            entry["source"] = source_name
            entry = fix_marker_order(entry)

            marked_text = entry.get("text_with_entity_marker", "")
            if marked_text in seen_marked_texts:
                duplicates += 1
                continue

            seen_marked_texts.add(marked_text)
            accepted_entries += 1
            accepted_records.append(entry)

            relations = entry.get("relation", [])
            if relations:
                for relation in relations:
                    relation_types[relation.get("PPI_relation_type", "Unknown")] += 1
            else:
                relation_types["None"] += 1

            text = entry.get("text", "")
            word_counts.append(count_words(text))
            sentence_counts.append(count_sentences(text))

        source_summaries[source_name] = SourceSummary(
            total=total_entries,
            accepted=accepted_entries,
            duplicates=duplicates,
            relation_types=relation_types,
            word_counts=word_counts,
            sentence_counts=sentence_counts,
        )
        all_records.extend(accepted_records)

    marker_patterns: Counter = Counter(
        extract_marker_pattern(record.get("text_with_entity_marker", "")) for record in all_records
    )
    marker_patterns = Counter({pattern: count for pattern, count in marker_patterns.items() if pattern})

    write_jsonl(output_path, all_records)
    report_markdown = build_analysis_report(all_records, source_summaries, marker_patterns)
    return CombinedDatasetResult(
        records=all_records,
        source_summaries=source_summaries,
        marker_patterns=marker_patterns,
        report_markdown=report_markdown,
    )
