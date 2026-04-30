#!/usr/bin/env python3
"""Local Streamlit app for expert audit of RLIMS-P v1 candidate relations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from phosphorylation_dataset.audit_labeling import (
    ENTITY_ROLES,
    VALID_PPI_LABELS,
    VALID_STATUSES,
    ConfirmedEntity,
    append_jsonl,
    build_decision,
    candidate_id,
    default_entity_from_relation,
    highlighted_text_html,
    latest_decisions,
    load_records,
    validate_entity_span,
    write_latest_decisions,
)


DEFAULT_CANDIDATES = PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_candidate_relations.json"
DEFAULT_NER = PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_ner_candidates.json"
DEFAULT_REJECTED = PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_rejected_relations.json"
DEFAULT_RAW = PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_raw_phosphorylation.json"
DEFAULT_DECISIONS = PROJECT_ROOT / "data" / "audit" / "rlims_p_v1_label_decisions.jsonl"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit RLIMS-P v1 candidate phosphorylation relations.")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--ner", type=Path, default=DEFAULT_NER)
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    return parser


def parse_args() -> argparse.Namespace:
    return build_argument_parser().parse_known_args()[0]


def latest_path_for(decisions_path: Path) -> Path:
    return decisions_path.with_name("rlims_p_v1_label_decisions_latest.json")


def source_record_id(candidate: dict) -> str:
    return str(candidate.get("source_record_id") or candidate.get("raw_id") or candidate.get("id", ""))


def choose_candidate(candidates: list[dict], latest_by_candidate: dict[str, dict]) -> dict | None:
    filter_mode = st.sidebar.radio(
        "Filter",
        ["unlabeled", "all", "approved", "rejected", "needs_change"],
        horizontal=False,
    )
    query = st.sidebar.text_input("Search PMID/PIR/id", "")

    filtered = []
    for candidate in candidates:
        cid = candidate_id(candidate)
        decision = latest_by_candidate.get(cid)
        if filter_mode == "unlabeled" and decision is not None:
            continue
        if filter_mode in VALID_STATUSES and (decision or {}).get("status") != filter_mode:
            continue
        haystack = " ".join(
            str(candidate.get(key, ""))
            for key in ("id", "candidate_id", "PMID", "PIR", "Kinase", "Substrate", "Site")
        ).lower()
        if query.strip() and query.lower() not in haystack:
            continue
        filtered.append(candidate)

    if not filtered:
        st.info("No candidates match the current filter.")
        return None

    if "candidate_index" not in st.session_state:
        st.session_state.candidate_index = 0
    st.session_state.candidate_index = min(st.session_state.candidate_index, len(filtered) - 1)

    labels = [
        f"{candidate_id(candidate)} | PMID={candidate.get('PMID', '')} | {candidate.get('Kinase', '')} -> {candidate.get('Substrate', '')}"
        for candidate in filtered
    ]
    selected = st.sidebar.selectbox(
        "Candidate",
        options=range(len(filtered)),
        index=st.session_state.candidate_index,
        format_func=lambda idx: labels[idx],
    )
    st.session_state.candidate_index = selected

    if st.sidebar.button("Next unlabeled"):
        for index, candidate in enumerate(filtered):
            if candidate_id(candidate) not in latest_by_candidate:
                st.session_state.candidate_index = index
                st.rerun()
        st.sidebar.info("No unlabeled candidates in this filter.")

    return filtered[st.session_state.candidate_index]


def candidate_spans(candidate: dict, *, include_ner: bool = False) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    relation = (candidate.get("relation") or [{}])[0]
    for index, label in ((1, "entity1"), (2, "entity2")):
        values = relation.get(f"entity_{index}_idx") or []
        if values:
            spans.append((int(values[0][0]), int(values[0][1]), label))
    for start, end in candidate.get("evidence_spans", []) or []:
        spans.append((int(start), int(end), "evidence"))
    if not include_ner:
        return spans
    for entity in candidate.get("ner_entities", []) or []:
        if "start" in entity and "end" in entity:
            spans.append((int(entity["start"]), int(entity["end"]), "ner"))
    return spans


def record_id(record: dict) -> str:
    return str(record.get("source_record_id") or record.get("raw_id") or record.get("id", ""))


def entity_role_counts(record: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in record.get("ner_entities", []) or []:
        role = str(entity.get("dictionary_role") or entity.get("label") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def ner_record_spans(record: dict) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for start, end in record.get("evidence_spans", []) or []:
        spans.append((int(start), int(end), "evidence"))
    for entity in record.get("ner_entities", []) or []:
        if "start" in entity and "end" in entity:
            role = str(entity.get("dictionary_role") or "ner")
            css_class = "ner"
            if role == "kinase":
                css_class = "entity1"
            elif role == "substrate":
                css_class = "entity2"
            spans.append((int(entity["start"]), int(entity["end"]), css_class))
    return spans


def pipeline_outcome(record: dict, candidates_by_source: dict[str, dict], rejected_by_id: dict[str, dict]) -> str:
    rid = record_id(record)
    if rid in candidates_by_source:
        return "strict_candidate"
    rejected = rejected_by_id.get(rid)
    if rejected:
        return str(rejected.get("rejection_reason") or "rejected")
    return "unknown"


def choose_ner_record(
    ner_records: list[dict],
    candidates_by_source: dict[str, dict],
    rejected_by_id: dict[str, dict],
) -> dict | None:
    st.sidebar.subheader("NER Pipeline Records")
    outcome_filter = st.sidebar.radio(
        "Pipeline outcome",
        [
            "all",
            "strict_candidate",
            "no_non_overlapping_kinase_substrate_pair",
            "autophosphorylation_requires_manual_entity_choice",
        ],
    )
    query = st.sidebar.text_input("Search NER PMID/PIR/id/entity", "")

    filtered = []
    for record in ner_records:
        outcome = pipeline_outcome(record, candidates_by_source, rejected_by_id)
        if outcome_filter != "all" and outcome != outcome_filter:
            continue
        haystack_parts = [
            str(record.get(key, ""))
            for key in ("id", "PMID", "PIR", "title", "ft_line", "declared_kinase_text")
        ]
        haystack_parts.extend(str(entity.get("text", "")) for entity in record.get("ner_entities", []) or [])
        haystack = " ".join(haystack_parts).lower()
        if query.strip() and query.lower() not in haystack:
            continue
        filtered.append(record)

    st.sidebar.write(f"Matching NER records: {len(filtered)}")
    if not filtered:
        st.info("No NER records match the current filter.")
        return None

    if "ner_record_index" not in st.session_state:
        st.session_state.ner_record_index = 0
    st.session_state.ner_record_index = min(st.session_state.ner_record_index, len(filtered) - 1)

    labels = [
        f"{record_id(record)} | PMID={record.get('PMID', '')} | {pipeline_outcome(record, candidates_by_source, rejected_by_id)}"
        for record in filtered
    ]
    selected = st.sidebar.selectbox(
        "NER record",
        options=range(len(filtered)),
        index=st.session_state.ner_record_index,
        format_func=lambda idx: labels[idx],
    )
    st.session_state.ner_record_index = selected
    return filtered[st.session_state.ner_record_index]


def render_ner_record(
    record: dict,
    candidate: dict | None,
    rejected: dict | None,
    candidates_by_source: dict[str, dict],
    rejected_by_id: dict[str, dict],
) -> None:
    rid = record_id(record)
    outcome = pipeline_outcome(record, candidates_by_source, rejected_by_id)
    role_counts = entity_role_counts(record)

    st.subheader(rid)
    cols = st.columns(5)
    cols[0].metric("PMID", record.get("PMID", ""))
    cols[1].metric("PIR", record.get("PIR", ""))
    cols[2].metric("Outcome", outcome)
    cols[3].metric("NER spans", len(record.get("ner_entities", []) or []))
    cols[4].metric("Evidence spans", len(record.get("evidence_spans", []) or []))

    st.caption(f"Title: {record.get('title', '')}")
    st.caption(f"FT: {record.get('ft_line', '')}")
    st.caption(
        f"Sites: {', '.join(record.get('phosphorylation_sites', []) or [])} | "
        f"Declared kinase: {record.get('declared_kinase_text', '')}"
    )

    style = """
    <style>
    .audit-text {font-size: 1rem; line-height: 1.7; border: 1px solid #ddd; padding: 1rem; border-radius: 4px;}
    mark.entity1 {background: #c7e9ff; padding: 0.1rem 0.2rem;}
    mark.entity2 {background: #ffd6a5; padding: 0.1rem 0.2rem;}
    mark.evidence {background: #fff2a8; padding: 0.1rem 0.2rem;}
    mark.ner {background: #e7ddff; padding: 0.1rem 0.2rem;}
    .trigger {font-weight: 700; color: #8a1c1c;}
    </style>
    """
    text = str(record.get("text", ""))
    st.markdown(
        style + f'<div class="audit-text">{highlighted_text_html(text, ner_record_spans(record))}</div>',
        unsafe_allow_html=True,
    )

    st.write("NER role counts:", role_counts)
    entities = record.get("ner_entities", []) or []
    if entities:
        st.dataframe(
            [
                {
                    "text": entity.get("text", ""),
                    "label": entity.get("label", ""),
                    "dictionary_role": entity.get("dictionary_role", ""),
                    "start": entity.get("start", ""),
                    "end": entity.get("end", ""),
                }
                for entity in entities
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning("No NER entities were detected for this record.")

    if candidate:
        relation = (candidate.get("relation") or [{}])[0]
        st.success(
            "Strict candidate created: "
            f"{relation.get('entity_1', '')} -> {relation.get('entity_2', '')} "
            f"({candidate.get('conversion_confidence', '')}, score={candidate.get('conversion_score', '')})"
        )
        with st.expander("Candidate relation JSON"):
            st.json(candidate)
    if rejected:
        st.warning(f"Rejected from strict candidate output: {rejected.get('rejection_reason', '')}")
        with st.expander("Rejected record JSON"):
            st.json(rejected)
    with st.expander("Full NER record JSON"):
        st.json(record)


def render_candidate(candidate: dict, raw_record: dict | None, latest_decision: dict | None) -> None:
    st.subheader(candidate_id(candidate))
    cols = st.columns(4)
    cols[0].metric("PMID", candidate.get("PMID", ""))
    cols[1].metric("PIR", candidate.get("PIR", ""))
    cols[2].metric("Confidence", candidate.get("conversion_confidence", ""))
    cols[3].metric("Latest", (latest_decision or {}).get("status", "unlabeled"))

    st.caption(f"FT: {candidate.get('FT') or candidate.get('ft_line') or ''}")
    st.caption(f"Site: {candidate.get('Site', '')} | Declared kinase: {candidate.get('declared_kinase_text', candidate.get('Kinase', ''))}")

    style = """
    <style>
    .audit-text {font-size: 1rem; line-height: 1.7; border: 1px solid #ddd; padding: 1rem; border-radius: 4px;}
    mark.entity1 {background: #c7e9ff; padding: 0.1rem 0.2rem;}
    mark.entity2 {background: #ffd6a5; padding: 0.1rem 0.2rem;}
    mark.evidence {background: #fff2a8; padding: 0.1rem 0.2rem;}
    mark.ner {background: #e7ddff; padding: 0.1rem 0.2rem;}
    .trigger {font-weight: 700; color: #8a1c1c;}
    </style>
    """
    text = str(candidate.get("text", ""))
    st.markdown(
        style + f'<div class="audit-text">{highlighted_text_html(text, candidate_spans(candidate))}</div>',
        unsafe_allow_html=True,
    )

    entities = candidate.get("ner_entities", []) or []
    if entities:
        with st.expander("NER spans available for P1/P2 selection"):
            st.dataframe(
                [
                    {
                        "text": entity.get("text", ""),
                        "label": entity.get("label", ""),
                        "dictionary_role": entity.get("dictionary_role", ""),
                        "start": entity.get("start", ""),
                        "end": entity.get("end", ""),
                    }
                    for entity in entities
                ],
                width="stretch",
                hide_index=True,
            )
    if raw_record:
        with st.expander("Raw source record"):
            st.json(raw_record)
    with st.expander("Candidate JSON"):
        st.json(candidate)
    if latest_decision:
        with st.expander("Latest decision"):
            st.json(latest_decision)


def entity_editor(prefix: str, default: ConfirmedEntity, text: str) -> ConfirmedEntity:
    st.markdown(f"**{prefix.replace('_', ' ').title()}**")
    cols = st.columns([2, 1, 1, 1])
    text_length = len(text)
    start_default = min(max(default.start, 0), text_length)
    end_default = min(max(default.end, start_default + 1), text_length) if text_length else 0
    entity_text = cols[0].text_input("Text", value=default.text, key=f"{prefix}_text")
    start = cols[1].number_input("Start", min_value=0, max_value=text_length, value=start_default, key=f"{prefix}_start")
    end = cols[2].number_input("End", min_value=0, max_value=text_length, value=end_default, key=f"{prefix}_end")
    role = cols[3].selectbox(
        "Role",
        options=ENTITY_ROLES,
        index=ENTITY_ROLES.index(default.role) if default.role in ENTITY_ROLES else ENTITY_ROLES.index("unknown"),
        key=f"{prefix}_role",
    )
    return ConfirmedEntity(text=entity_text, start=int(start), end=int(end), role=role)


def entity_key(entity: ConfirmedEntity) -> tuple[int, int, str]:
    return (entity.start, entity.end, entity.text)


def valid_text_entity(text: str, entity: ConfirmedEntity) -> bool:
    return (
        0 <= entity.start < entity.end <= len(text)
        and text[entity.start : entity.end] == entity.text
    )


def candidate_entity_options(candidate: dict, latest_decision: dict | None, text: str) -> list[ConfirmedEntity]:
    """Return selectable P1/P2 options backed by actual source-text spans."""
    options: list[ConfirmedEntity] = []

    for relation_index in (1, 2):
        default = default_entity_from_relation(candidate, relation_index)
        if valid_text_entity(text, default):
            options.append(default)

    for key in ("confirmed_entity_1", "confirmed_entity_2"):
        if latest_decision and isinstance(latest_decision.get(key), dict):
            entity = ConfirmedEntity.from_mapping(latest_decision[key])
            if valid_text_entity(text, entity):
                options.append(entity)

    for entity in candidate.get("ner_entities", []) or []:
        try:
            start = int(entity.get("start", -1))
            end = int(entity.get("end", -1))
        except (TypeError, ValueError):
            continue
        entity_text = str(entity.get("text", ""))
        role = str(entity.get("dictionary_role") or "protein")
        if role not in ENTITY_ROLES:
            role = "protein"
        option = ConfirmedEntity(text=entity_text, start=start, end=end, role=role)
        if valid_text_entity(text, option):
            options.append(option)

    unique: dict[tuple[int, int, str], ConfirmedEntity] = {}
    for option in options:
        unique.setdefault(entity_key(option), option)
    return sorted(unique.values(), key=lambda item: (item.start, item.end, item.text.lower()))


def format_entity_option(entity: ConfirmedEntity) -> str:
    return f"{entity.text} [{entity.start}:{entity.end}] role={entity.role}"


def entity_picker(
    label: str,
    *,
    options: list[ConfirmedEntity],
    default: ConfirmedEntity,
    latest_entity: ConfirmedEntity | None,
    default_role: str,
) -> ConfirmedEntity:
    st.markdown(f"**{label}**")
    preferred = latest_entity or default
    preferred_key = entity_key(preferred)
    selected_index = 0
    for index, option in enumerate(options):
        if entity_key(option) == preferred_key:
            selected_index = index
            break

    selected = st.selectbox(
        f"{label} span from source text",
        options=range(len(options)),
        index=selected_index,
        format_func=lambda idx: format_entity_option(options[idx]),
        key=f"{label}_span",
    )
    selected_entity = options[int(selected)]
    role = st.selectbox(
        f"{label} role",
        options=ENTITY_ROLES,
        index=ENTITY_ROLES.index(default_role) if default_role in ENTITY_ROLES else ENTITY_ROLES.index(selected_entity.role),
        key=f"{label}_role",
    )
    locked = ConfirmedEntity(
        text=selected_entity.text,
        start=selected_entity.start,
        end=selected_entity.end,
        role=role,
    )
    st.caption(f"Locked source span: `{locked.text}` at `{locked.start}:{locked.end}`")
    return locked


def decision_entity(latest_decision: dict | None, key: str, fallback: ConfirmedEntity) -> ConfirmedEntity:
    if latest_decision and isinstance(latest_decision.get(key), dict):
        return ConfirmedEntity.from_mapping(latest_decision[key])
    return fallback


def save_decision(
    *,
    candidate: dict,
    decisions_path: Path,
    latest_path: Path,
    latest_decision: dict | None,
    status: str,
    ppi_label: str,
    reviewer: str,
    entity_1: ConfirmedEntity,
    entity_2: ConfirmedEntity,
    confirmed_site: str,
    notes: str,
) -> None:
    text = str(candidate.get("text", ""))
    validate_entity_span(text, entity_1)
    validate_entity_span(text, entity_2)
    decision = build_decision(
        candidate_id_value=candidate_id(candidate),
        reviewer=reviewer,
        status=status,
        ppi_label=ppi_label,
        confirmed_entity_1=entity_1,
        confirmed_entity_2=entity_2,
        confirmed_site=confirmed_site,
        notes=notes,
        supersedes_decision_id=(latest_decision or {}).get("decision_id"),
    )
    append_jsonl(decisions_path, decision)
    write_latest_decisions(decisions_path, latest_path)


def main() -> None:
    args = parse_args()
    st.set_page_config(page_title="RLIMS-P v1 Audit", layout="wide")
    st.title("RLIMS-P v1 NER Pipeline Viewer and Expert PPI Labeling")

    candidates = load_records(args.candidates)
    ner_records = load_records(args.ner)
    rejected_records = load_records(args.rejected)
    raw_records = {str(record.get("id", "")): record for record in load_records(args.raw)}
    decisions = load_records(args.decisions)
    latest = latest_decisions(decisions)
    candidates_by_source = {source_record_id(candidate): candidate for candidate in candidates}
    rejected_by_id = {record_id(record): record for record in rejected_records}

    view_mode = st.sidebar.radio(
        "View",
        ["NER pipeline view (all 89 records)", "Expert audit view (strict candidates)"],
    )

    if view_mode == "NER pipeline view (all 89 records)":
        if not ner_records:
            st.error(f"No NER records found at {args.ner}")
            return

        st.sidebar.write(f"NER records: {len(ner_records)}")
        st.sidebar.write(f"Strict candidates: {len(candidates)}")
        st.sidebar.write(f"Rejected from strict output: {len(rejected_records)}")

        st.info(
            "This view shows every RLIMS-P v1 record after the NER pipeline. "
            "A record becomes a strict candidate only if the converter can place exact, non-overlapping [E1]/[E2] offsets."
        )
        record = choose_ner_record(ner_records, candidates_by_source, rejected_by_id)
        if record is None:
            return
        rid = record_id(record)
        render_ner_record(
            record,
            candidates_by_source.get(rid),
            rejected_by_id.get(rid),
            candidates_by_source,
            rejected_by_id,
        )
        return

    if not candidates:
        st.error(f"No candidate records found at {args.candidates}")
        return

    st.sidebar.subheader("Strict Candidate Audit")
    st.sidebar.write(f"Candidates: {len(candidates)}")
    st.sidebar.write(f"Decisions: {len(decisions)}")
    st.sidebar.write(f"Latest labels: {len(latest)}")

    candidate = choose_candidate(candidates, latest)
    if candidate is None:
        return

    cid = candidate_id(candidate)
    latest_decision = latest.get(cid)
    raw_record = raw_records.get(source_record_id(candidate))
    render_candidate(candidate, raw_record, latest_decision)

    st.divider()
    st.subheader("Decision")
    text = str(candidate.get("text", ""))
    default_entity_1 = default_entity_from_relation(candidate, 1)
    default_entity_2 = default_entity_from_relation(candidate, 2)
    latest_entity_1 = (
        ConfirmedEntity.from_mapping(latest_decision["confirmed_entity_1"])
        if latest_decision and isinstance(latest_decision.get("confirmed_entity_1"), dict)
        else None
    )
    latest_entity_2 = (
        ConfirmedEntity.from_mapping(latest_decision["confirmed_entity_2"])
        if latest_decision and isinstance(latest_decision.get("confirmed_entity_2"), dict)
        else None
    )
    entity_options = candidate_entity_options(candidate, latest_decision, text)
    if not entity_options:
        st.error("No valid source-text entity spans are available for this candidate.")
        return

    reviewer = st.text_input("Reviewer", value=(latest_decision or {}).get("reviewer", ""))
    cols = st.columns(2)
    status_options = ("",) + VALID_STATUSES
    label_options = ("",) + VALID_PPI_LABELS
    current_status = (latest_decision or {}).get("status", "")
    current_label = (latest_decision or {}).get("ppi_label", "")
    status = cols[0].selectbox(
        "Status",
        options=status_options,
        index=status_options.index(current_status) if current_status in status_options else 0,
    )
    ppi_label = cols[1].selectbox(
        "PPI label",
        options=label_options,
        index=label_options.index(current_label) if current_label in label_options else 0,
    )

    st.caption(
        "P1 and P2 must be selected from detected source-text spans. "
        "The text/start/end fields are locked to the selected span and cannot be typed manually."
    )

    pcols = st.columns(2)
    with pcols[0]:
        entity_1 = entity_picker(
            "P1",
            options=entity_options,
            default=default_entity_1,
            latest_entity=latest_entity_1,
            default_role=(latest_entity_1 or default_entity_1).role,
        )
    with pcols[1]:
        entity_2 = entity_picker(
            "P2",
            options=entity_options,
            default=default_entity_2,
            latest_entity=latest_entity_2,
            default_role=(latest_entity_2 or default_entity_2).role,
        )

    if entity_key(entity_1) == entity_key(entity_2):
        st.error("P1 and P2 must be different source-text spans.")

    selected_preview_spans = [
        (entity_1.start, entity_1.end, "entity1"),
        (entity_2.start, entity_2.end, "entity2"),
    ]
    st.markdown(
        '<div class="audit-text">'
        + highlighted_text_html(text, selected_preview_spans)
        + "</div>",
        unsafe_allow_html=True,
    )
    confirmed_site = st.text_input(
        "Confirmed site",
        value=str((latest_decision or {}).get("confirmed_site") or candidate.get("Site", "")),
    )
    notes = st.text_area("Notes", value="")
    confirmed = st.checkbox("I confirm this decision and the entity offsets.")

    latest_path = latest_path_for(args.decisions)
    different_entities = entity_key(entity_1) != entity_key(entity_2)
    can_save = bool(reviewer.strip() and status and ppi_label and confirmed and different_entities)

    cols = st.columns(4)
    if cols[0].button("Save decision", disabled=not can_save):
        try:
            save_decision(
                candidate=candidate,
                decisions_path=args.decisions,
                latest_path=latest_path,
                latest_decision=latest_decision,
                status=status,
                ppi_label=ppi_label,
                reviewer=reviewer,
                entity_1=entity_1,
                entity_2=entity_2,
                confirmed_site=confirmed_site,
                notes=notes,
            )
            st.success("Decision saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if cols[1].button("Reject candidate", disabled=not bool(reviewer.strip() and confirmed and different_entities)):
        try:
            save_decision(
                candidate=candidate,
                decisions_path=args.decisions,
                latest_path=latest_path,
                latest_decision=latest_decision,
                status="rejected",
                ppi_label="no_relation",
                reviewer=reviewer,
                entity_1=entity_1,
                entity_2=entity_2,
                confirmed_site=confirmed_site,
                notes=notes,
            )
            st.success("Candidate rejected.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if cols[2].button("Mark needs change", disabled=not bool(reviewer.strip() and confirmed and different_entities)):
        try:
            save_decision(
                candidate=candidate,
                decisions_path=args.decisions,
                latest_path=latest_path,
                latest_decision=latest_decision,
                status="needs_change",
                ppi_label=ppi_label or "uncertain",
                reviewer=reviewer,
                entity_1=entity_1,
                entity_2=entity_2,
                confirmed_site=confirmed_site,
                notes=notes,
            )
            st.success("Candidate marked as needs_change.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if cols[3].button("Revise previous decision", disabled=latest_decision is None or not can_save):
        try:
            save_decision(
                candidate=candidate,
                decisions_path=args.decisions,
                latest_path=latest_path,
                latest_decision=latest_decision,
                status=status,
                ppi_label=ppi_label,
                reviewer=reviewer,
                entity_1=entity_1,
                entity_2=entity_2,
                confirmed_site=confirmed_site,
                notes=notes,
            )
            st.success("Revision saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


if __name__ == "__main__":
    main()
