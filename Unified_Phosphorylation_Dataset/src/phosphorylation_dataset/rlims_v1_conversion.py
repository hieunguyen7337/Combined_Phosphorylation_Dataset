"""Generate auditable RLIMS-P v1 phosphorylation candidates with biomedical NER."""

from __future__ import annotations

import csv
import html.parser
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .io_utils import write_jsonl


GENE_LABELS = {"GENE_OR_GENE_PRODUCT", "PROTEIN", "protein"}
TRIGGER_RE = re.compile(r"\b(phosphorylat\w*|phospho\w*)\b", re.IGNORECASE)
AMINO_ACID_WORDS = {
    "ala",
    "arg",
    "asn",
    "asp",
    "cys",
    "gln",
    "glu",
    "gly",
    "his",
    "ile",
    "leu",
    "lys",
    "met",
    "phe",
    "pro",
    "ser",
    "thr",
    "trp",
    "tyr",
    "val",
    "alanine",
    "arginine",
    "asparagine",
    "aspartate",
    "cysteine",
    "glutamate",
    "glutamine",
    "glycine",
    "histidine",
    "isoleucine",
    "leucine",
    "lysine",
    "methionine",
    "phenylalanine",
    "proline",
    "serine",
    "threonine",
    "tryptophan",
    "tyrosine",
    "valine",
}


@dataclass(frozen=True)
class RlimsV1Feature:
    """One RLIMS-P v1 FT/abstract feature record."""

    ordinal: int
    feature_index: int
    pmid: str
    pir: str
    ft_line: str
    title: str
    marked_abstract: str
    abstract: str
    evidence_spans: list[tuple[int, int]]
    source: str

    @property
    def record_id(self) -> str:
        return f"rlims_p_v1_PMID{self.pmid}_{self.pir}_FT{self.feature_index}"


class MarkedHtmlParser(html.parser.HTMLParser):
    """Convert the source SHTML to text while preserving red evidence markers."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")
        if tag.lower() == "font" and dict(attrs).get("color", "").lower() == "red":
            self.parts.append("[[RED_START]]")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "font":
            self.parts.append("[[RED_END]]")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts).replace("\xa0", " ")


@dataclass(frozen=True)
class RlimsV1ConversionResult:
    raw_records: list[dict]
    ner_records: list[dict]
    candidate_records: list[dict]
    rejected_records: list[dict]
    report_markdown: str


def clean_text(value: str) -> str:
    """Collapse whitespace to match the existing normalized corpus style."""
    return re.sub(r"\s+", " ", value).strip()


def plain_text_with_spans(marked_text: str) -> tuple[str, list[tuple[int, int]]]:
    """Remove red evidence markers and return their plain-text spans."""
    plain_parts: list[str] = []
    spans: list[tuple[int, int]] = []
    cursor = 0
    in_red = False
    red_start = 0
    token_re = re.compile(r"\[\[RED_START\]\]|\[\[RED_END\]\]")

    position = 0
    for match in token_re.finditer(marked_text):
        chunk = marked_text[position : match.start()]
        plain_parts.append(chunk)
        cursor += len(chunk)
        marker = match.group(0)
        if marker == "[[RED_START]]":
            in_red = True
            red_start = cursor
        elif marker == "[[RED_END]]" and in_red:
            spans.append((red_start, cursor))
            in_red = False
        position = match.end()

    tail = marked_text[position:]
    plain_parts.append(tail)
    cursor += len(tail)
    if in_red:
        spans.append((red_start, cursor))
    return "".join(plain_parts), spans


def parse_rlims_v1_ie(path: Path) -> list[RlimsV1Feature]:
    """Parse RLIMS-P v1 IE SHTML into structured feature records."""
    parser = MarkedHtmlParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = parser.text()
    features: list[RlimsV1Feature] = []

    heading_matches = list(re.finditer(r"\n\s*(\d+)\. PMID\s*:\s*(\d+)", text))
    for heading_index, heading in enumerate(heading_matches):
        ordinal = int(heading.group(1))
        pmid = heading.group(2)
        start = heading.end()
        end = heading_matches[heading_index + 1].start() if heading_index + 1 < len(heading_matches) else len(text)
        body = text[start:end]
        section_re = re.compile(
            r"PIR\s*:\s*([A-Za-z0-9]+)\s*\n\s*FT\s*-\s*(.*?)\n\s*TI\s*-\s*(.*?)\n\s*AB\s*-\s*(.*?)\n\s*SO\s*-\s*(.*?)(?=\n\s*PIR\s*:|\Z)",
            re.S,
        )
        for feature_index, section in enumerate(section_re.finditer(body), 1):
            pir, ft_line, title, abstract, source = section.groups()
            marked_abstract = clean_text(abstract)
            plain_abstract, evidence_spans = plain_text_with_spans(marked_abstract)
            features.append(
                RlimsV1Feature(
                    ordinal=ordinal,
                    feature_index=feature_index,
                    pmid=pmid,
                    pir=pir,
                    ft_line=clean_text(ft_line),
                    title=clean_text(title),
                    marked_abstract=marked_abstract,
                    abstract=clean_text(plain_abstract),
                    evidence_spans=evidence_spans,
                    source=clean_text(source),
                )
            )
    return features


def parse_site_values(ft_line: str) -> tuple[str, list[str]]:
    """Extract residue code and sequence positions from a PIR feature line."""
    residue_match = re.search(r"phosphate\s+\(([^)]+)\)", ft_line, re.IGNORECASE)
    position_match = re.search(r"\|\s*([0-9,\s]+)(?:\(|$)", ft_line)
    if not residue_match or not position_match:
        return "", []
    residue = residue_match.group(1).strip()
    positions = [position.strip() for position in position_match.group(1).split(",") if position.strip()]
    return residue, [f"{residue}{position}" for position in positions]


def declared_kinase(ft_line: str) -> str:
    """Extract the optional '(by ...)' kinase phrase from a PIR feature line."""
    match = re.search(r"\(by ([^)]+)\)", ft_line, re.IGNORECASE)
    if not match:
        return ""
    kinase = clean_text(match.group(1))
    if kinase.lower() in {"autophosphorylation", "unidentified kinase"}:
        return kinase
    return kinase


def sentence_window(text: str, spans: list[tuple[int, int]]) -> tuple[str, int]:
    """Return the sentence containing the first evidence span, or the abstract."""
    if not spans:
        return text, 0
    start, end = spans[0]
    sentence_start = max(text.rfind(". ", 0, start), text.rfind("? ", 0, start), text.rfind("! ", 0, start))
    sentence_start = 0 if sentence_start == -1 else sentence_start + 2
    sentence_end_candidates = [pos for pos in (text.find(". ", end), text.find("? ", end), text.find("! ", end)) if pos != -1]
    sentence_end = min(sentence_end_candidates) + 1 if sentence_end_candidates else len(text)
    return text[sentence_start:sentence_end].strip(), sentence_start


def load_iptmnet_dictionary(zip_path: Path) -> tuple[set[str], set[str]]:
    """Load kinase and substrate symbols from the local IPTMNet export."""
    kinases: set[str] = set()
    substrates: set[str] = set()
    if not zip_path.exists():
        return kinases, substrates

    with zipfile.ZipFile(zip_path) as archive:
        for name in ("deploy/MV_EVENT_DATA_TABLE.csv", "deploy/MV_EFIP_DATA_TABLE.csv", "deploy/MV_PROTEO_DATA_TABLE.csv"):
            if name not in archive.namelist():
                continue
            with archive.open(name) as handle:
                reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8", newline=""))
                for row in reader:
                    event = row.get("EVENT_NAME") or row.get("PTM_EVENT_NAME") or ""
                    if event != "Phosphorylation":
                        continue
                    kinase = row.get("ENZ_SYMBOL") or row.get("PTM_ENZ_SYMBOL") or ""
                    substrate = row.get("SUB_SYMBOL") or row.get("PTM_SUB_SYMBOL") or row.get("PPI_SUB_SYMBOL") or ""
                    if kinase.strip():
                        kinases.add(kinase.strip().upper())
                    if substrate.strip():
                        substrates.add(substrate.strip().upper())
    return kinases, substrates


def kinase_aliases(kinase: str) -> set[str]:
    """Build common aliases for kinase phrases found in older abstracts."""
    if not kinase:
        return set()
    aliases = {kinase, kinase.replace("-", " ")}
    lower = kinase.lower()
    manual = {
        "protein kinase c": {"PKC", "protein kinase C"},
        "protein kinase a": {"PKA", "protein kinase A"},
        "camp-dependent kinase": {"PKA", "cAMP-dependent protein kinase", "cyclic-AMP-dependent protein kinase"},
        "camp- and cgmp-dependent kinases": {"PKA", "PKG", "cAMP-dependent protein kinase", "cGMP-dependent protein kinase"},
        "casein kinase ii": {"CK-II", "CKII", "CK2", "casein kinase II"},
        "cdc2 kinase": {"cdc2 kinase", "p34cdc2", "p34-cdc2"},
        "map and cdc2 kinases": {"MAP kinase", "cdc2 kinase", "p34cdc2", "p34-cdc2"},
    }
    for key, values in manual.items():
        if key in lower:
            aliases.update(values)
    initials = "".join(word[0] for word in re.findall(r"[A-Za-z]+", kinase) if word.lower() not in {"and", "by", "dependent"})
    if len(initials) >= 2:
        aliases.add(initials.upper())
    return {alias for alias in aliases if alias}


def run_ner(nlp, text: str) -> list[dict]:
    """Run the configured NER model and return normalized entity dictionaries."""
    entities: list[dict] = []
    seen: set[tuple[int, int, str]] = set()
    for ent in nlp(text).ents:
        if ent.label_ not in GENE_LABELS:
            continue
        key = (ent.start_char, ent.end_char, ent.text)
        if key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
        )
    return entities


def role_for_entity(entity: dict, kinases: set[str], substrates: set[str]) -> str:
    key = str(entity["text"]).upper()
    in_kinase = key in kinases
    in_substrate = key in substrates
    if in_kinase and not in_substrate:
        return "kinase"
    if in_substrate and not in_kinase:
        return "substrate"
    if in_kinase and in_substrate:
        return "kinase_or_substrate"
    return "protein"


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def is_bad_entity_text(value: str) -> bool:
    """Filter common NER artifacts that are not useful protein mentions."""
    text = value.strip()
    lower = text.lower().strip(".,;:()")
    compact = re.sub(r"[^A-Za-z0-9]", "", text)
    if len(compact) < 2:
        return True
    if lower in AMINO_ACID_WORDS:
        return True
    if re.fullmatch(r"(Ser|Thr|Tyr|Asp|His|Arg|serine|threonine|tyrosine)[- ]?\d+", text, re.IGNORECASE):
        return True
    if re.fullmatch(r"serines?|threonines?|tyrosines?", text, re.IGNORECASE):
        return True
    if re.fullmatch(r"[A-Z]{5,}", compact) and not re.search(r"\d|-", text):
        return True
    return False


def score_entity_near_spans(entity: dict, spans: list[tuple[int, int]]) -> int:
    if not spans:
        return 0
    start = int(entity["start"])
    end = int(entity["end"])
    score = 0
    for span_start, span_end in spans:
        if start >= span_start and end <= span_end:
            score += 8
        distance = min(abs(start - span_end), abs(span_start - end))
        if distance <= 80:
            score += 4
        elif distance <= 200:
            score += 2
    return score


def score_kinase(entity: dict, feature: RlimsV1Feature, kinases: set[str]) -> int:
    if is_bad_entity_text(str(entity["text"])):
        return 0
    score = 0
    aliases = {normalize_for_match(alias) for alias in kinase_aliases(declared_kinase(feature.ft_line))}
    if normalize_for_match(str(entity["text"])) in aliases:
        score += 20
    if str(entity["text"]).upper() in kinases:
        score += 7
    if "kinase" in str(entity["text"]).lower():
        score += 5
    if score == 0:
        return 0
    score += score_entity_near_spans(entity, feature.evidence_spans)
    return score


def score_substrate(entity: dict, feature: RlimsV1Feature, substrates: set[str]) -> int:
    text = feature.abstract
    start = int(entity["start"])
    end = int(entity["end"])
    entity_text = str(entity["text"])
    entity_key = entity_text.upper()
    declared_aliases = {normalize_for_match(alias) for alias in kinase_aliases(declared_kinase(feature.ft_line))}
    role = str(entity.get("dictionary_role", ""))
    if (
        is_bad_entity_text(entity_text)
        or
        role == "kinase"
        or normalize_for_match(entity_text) in declared_aliases
        or entity_key in getattr(score_substrate, "_kinases", set())
        or re.search(r"\bkinase\b", entity_text, re.IGNORECASE)
    ):
        return 0

    score = 0
    if entity_key in substrates:
        score += 5
    evidence_score = score_entity_near_spans(entity, feature.evidence_spans)
    before = text[max(0, start - 45) : start].lower()
    after = text[end : min(len(text), end + 45)].lower()
    if re.search(r"\bby\b[^.;,]{0,35}$", before):
        return 0
    if re.search(r"\bnot\s+phosphorylated\b", after):
        return 0
    explicit_pattern = False
    passive_after = re.match(r"\s*(?:was|were|is|are|becomes|became)\s+phosphorylated\b", after)
    object_before = re.search(r"\bphosphorylated\s+$", before)
    if "phosphorylation of" in before or passive_after or object_before:
        score += 10
        explicit_pattern = True
    if TRIGGER_RE.search(before) or TRIGGER_RE.search(after):
        score += 3
    if evidence_score >= 8 and role not in {"kinase", "kinase_or_substrate"}:
        score += evidence_score
    elif explicit_pattern:
        score += min(evidence_score, 4)
    return score


def insert_markers(text: str, first: dict, second: dict) -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Insert markers around non-overlapping entity spans."""
    if int(first["start"]) > int(second["start"]):
        first, second = second, first
    first_start, first_end = int(first["start"]), int(first["end"])
    second_start, second_end = int(second["start"]), int(second["end"])
    if first_end > second_start:
        raise ValueError("Overlapping entity spans are not supported.")
    prefix = text[:first_start]
    first_text = text[first_start:first_end]
    middle = text[first_end:second_start]
    second_text = text[second_start:second_end]
    suffix = text[second_end:]
    marked = f"{prefix}[E1]{first_text}[/E1]{middle}[E2]{second_text}[/E2]{suffix}"
    first_marked = (len(prefix) + len("[E1]"), len(prefix) + len("[E1]") + len(first_text))
    second_marked_start = len(prefix) + len("[E1]") + len(first_text) + len("[/E1]") + len(middle) + len("[E2]")
    second_marked = (second_marked_start, second_marked_start + len(second_text))
    return marked, first_marked, second_marked


def choose_pair(feature: RlimsV1Feature, entities: list[dict], kinases: set[str], substrates: set[str]) -> tuple[dict | None, str]:
    """Choose one auditable kinase/substrate candidate pair."""
    declared = declared_kinase(feature.ft_line)
    if declared.lower() == "autophosphorylation":
        return None, "autophosphorylation_requires_manual_entity_choice"

    score_substrate._kinases = kinases
    kinase_scores = [(score_kinase(entity, feature, kinases), entity) for entity in entities]
    substrate_scores = [(score_substrate(entity, feature, substrates), entity) for entity in entities]
    kinase_scores = sorted([item for item in kinase_scores if item[0] > 0], key=lambda item: item[0], reverse=True)
    substrate_scores = sorted([item for item in substrate_scores if item[0] >= 8], key=lambda item: item[0], reverse=True)

    best: tuple[int, dict, dict] | None = None
    for kinase_score, kinase_entity in kinase_scores:
        for substrate_score, substrate_entity in substrate_scores:
            if kinase_entity is substrate_entity:
                continue
            if int(kinase_entity["start"]) < int(substrate_entity["end"]) and int(substrate_entity["start"]) < int(kinase_entity["end"]):
                continue
            total = kinase_score + substrate_score
            if best is None or total > best[0]:
                best = (total, kinase_entity, substrate_entity)

    if best is None:
        return None, "no_non_overlapping_kinase_substrate_pair"

    total, kinase_entity, substrate_entity = best
    confidence = "high" if total >= 35 else "medium" if total >= 22 else "low"
    return {
        "kinase": kinase_entity,
        "substrate": substrate_entity,
        "score": total,
        "confidence": confidence,
    }, ""


def raw_record(feature: RlimsV1Feature) -> dict:
    residue, sites = parse_site_values(feature.ft_line)
    return {
        "id": feature.record_id,
        "PMID": feature.pmid,
        "PIR": feature.pir,
        "title": feature.title,
        "text": feature.abstract,
        "full_abstract": feature.abstract,
        "ft_line": feature.ft_line,
        "feature_type": feature.ft_line.split("|", 1)[0].strip(),
        "phosphorylation_residue": residue,
        "phosphorylation_sites": sites,
        "declared_kinase_text": declared_kinase(feature.ft_line),
        "evidence_spans": feature.evidence_spans,
        "source_reference": feature.source,
        "source": "rlims_p_v1",
    }


def candidate_record(feature: RlimsV1Feature, entities: list[dict], pair: dict) -> dict:
    residue, sites = parse_site_values(feature.ft_line)
    kinase = pair["kinase"]
    substrate = pair["substrate"]
    first, second = (substrate, kinase) if int(substrate["start"]) <= int(kinase["start"]) else (kinase, substrate)
    marked, first_marked, second_marked = insert_markers(feature.abstract, first, second)
    return {
        "id": f"{feature.record_id}_CAND1",
        "candidate_id": f"{feature.record_id}_CAND1",
        "source_record_id": feature.record_id,
        "text": feature.abstract,
        "text_with_entity_marker": marked,
        "relation": [
            {
                "PPI_relation_type": "phosphorylation_candidate",
                "relation_id": 0,
                "entity_1": first["text"],
                "entity_1_idx": [[first["start"], first["end"]]],
                "entity_1_idx_in_text_with_entity_marker": [first_marked[0], first_marked[1]],
                "entity_1_type": "protein",
                "entity_1_type_id": 0,
                "entity_2": second["text"],
                "entity_2_idx": [[second["start"], second["end"]]],
                "entity_2_idx_in_text_with_entity_marker": [second_marked[0], second_marked[1]],
                "entity_2_type": "protein",
                "entity_2_type_id": 0,
            }
        ],
        "PMID": feature.pmid,
        "PIR": feature.pir,
        "FT": feature.ft_line,
        "Kinase": kinase["text"],
        "Substrate": substrate["text"],
        "Site": ", ".join(sites),
        "PPI": "phosphorylation_candidate",
        "Interactant": kinase["text"],
        "ner_entities": entities,
        "evidence_spans": feature.evidence_spans,
        "declared_kinase_text": declared_kinase(feature.ft_line),
        "conversion_score": pair["score"],
        "conversion_confidence": pair["confidence"],
        "conversion_method": "bionlp13cg_ner_plus_ft_kinase_plus_trigger_rules",
        "requires_manual_audit": True,
        "source": "rlims_p_v1",
    }


def write_brat_record(output_dir: Path, record: dict) -> None:
    """Write a simple BRAT view of one candidate record."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / record["id"]
    base.with_suffix(".txt").write_text(record["text"], encoding="utf-8")
    lines: list[str] = []
    tid = 1
    for entity in record.get("ner_entities", []):
        lines.append(f"T{tid}\tProtein {entity['start']} {entity['end']}\t{entity['text']}")
        tid += 1
    for start, end in record.get("evidence_spans", []):
        lines.append(f"T{tid}\tEvidence {start} {end}\t{record['text'][start:end]}")
        tid += 1
    base.with_suffix(".ann").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_report(raw: list[dict], candidates: list[dict], rejected: list[dict]) -> str:
    confidence = Counter(record.get("conversion_confidence", "") for record in candidates)
    reasons = Counter(record.get("rejection_reason", "") for record in rejected)
    lines = [
        "# RLIMS-P v1 NER Candidate Conversion",
        "",
        f"Raw feature records: {len(raw)}",
        f"Candidate relations: {len(candidates)}",
        f"Rejected records: {len(rejected)}",
        "",
        "## Candidate Confidence",
        "",
    ]
    for name, count in confidence.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Rejection Reasons", ""])
    for name, count in reasons.most_common():
        lines.append(f"- {name}: {count}")
    lines.append("")
    lines.append("All candidate relations require manual audit before export into the unified dataset.")
    return "\n".join(lines)


def convert_rlims_v1(
    *,
    input_path: Path,
    iptmnet_zip: Path,
    raw_output: Path,
    ner_output: Path,
    candidate_output: Path,
    rejected_output: Path,
    report_path: Path,
    brat_output: Path | None = None,
    model_name: str = "en_ner_bionlp13cg_md",
) -> RlimsV1ConversionResult:
    """Run the RLIMS-P v1 NER candidate conversion pipeline."""
    import spacy

    features = parse_rlims_v1_ie(input_path)
    kinases, substrates = load_iptmnet_dictionary(iptmnet_zip)
    nlp = spacy.load(model_name)
    if brat_output is not None and brat_output.exists():
        for stale_file in list(brat_output.glob("*.ann")) + list(brat_output.glob("*.txt")):
            stale_file.unlink()

    raw_records: list[dict] = []
    ner_records: list[dict] = []
    candidate_records: list[dict] = []
    rejected_records: list[dict] = []

    for feature in features:
        raw = raw_record(feature)
        entities = run_ner(nlp, feature.abstract)
        for entity in entities:
            entity["dictionary_role"] = role_for_entity(entity, kinases, substrates)
        ner_record = dict(raw)
        ner_record["ner_entities"] = entities
        raw_records.append(raw)
        ner_records.append(ner_record)

        pair, rejection_reason = choose_pair(feature, entities, kinases, substrates)
        if pair is None:
            rejected = dict(ner_record)
            rejected["rejection_reason"] = rejection_reason
            rejected_records.append(rejected)
            continue

        candidate = candidate_record(feature, entities, pair)
        candidate_records.append(candidate)
        if brat_output is not None:
            write_brat_record(brat_output, candidate)

    report = build_report(raw_records, candidate_records, rejected_records)
    write_jsonl(raw_output, raw_records)
    write_jsonl(ner_output, ner_records)
    write_jsonl(candidate_output, candidate_records)
    write_jsonl(rejected_output, rejected_records)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    return RlimsV1ConversionResult(
        raw_records=raw_records,
        ner_records=ner_records,
        candidate_records=candidate_records,
        rejected_records=rejected_records,
        report_markdown=report,
    )
