# CLAUDE.md

This repository contains phosphorylation text-mining datasets and conversion tooling for building a unified phosphorylation/PPI corpus. The current active work is converting `rlims_p_v1` into auditable candidate relations compatible with the format used by `Unified_Phosphorylation_Dataset`.

## Current Repository Context

Workspace root:

```powershell
F:\document\QUT_research_assistant_file\Dr_Bashar_file\Phos_dataset
```

Important directories:

- `Unified_Phosphorylation_Dataset/` - main conversion code, processed outputs, audit tooling, reports.
- `rlims_p_v1/` - downloaded RLIMS-P v1 benchmarking files.
- `rlims_p_v2/` - existing RLIMS-P v2 source data.
- `eFIP/` - existing dataset folder, excluded from the new folder exploration requirement.
- `miRTex/` - extracted from tar; not the current active conversion target.
- `Text_mining_UDel/` - contains downloaded iProLINK/UDel corpora and `iptmnet5.1.zip`, used as a local kinase/substrate dictionary source.

Python environment:

```powershell
.\.venv\Scripts\python.exe
```

The virtual environment has the NER/conversion dependencies installed, including `spacy`, `scispacy`, `en_ner_bionlp13cg_md`, and `streamlit`.

## User Goal

The user wants `rlims_p_v1` converted into an auditable phosphorylation relation dataset. The important requirement is exact `[E1]` and `[E2]` relation markers with direct offsets in the source biomedical paper abstract text.

The user clarified that they want the actual NER pipeline run, not only the Streamlit audit app.

## Implemented Files

Core NER conversion:

- `Unified_Phosphorylation_Dataset/convert_rlims_p_v1_to_json.py`
- `Unified_Phosphorylation_Dataset/src/phosphorylation_dataset/rlims_v1_conversion.py`

Audit and export tooling:

- `Unified_Phosphorylation_Dataset/audit_rlims_p_v1_labels.py`
- `Unified_Phosphorylation_Dataset/export_audited_rlims_p_v1.py`
- `Unified_Phosphorylation_Dataset/src/phosphorylation_dataset/audit_labeling.py`

Dependency file:

- `Unified_Phosphorylation_Dataset/requirements-ner.txt`

Documentation updated:

- `Unified_Phosphorylation_Dataset/README.md`

Generated output files:

- `Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_raw_phosphorylation.json`
- `Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_ner_candidates.json`
- `Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_candidate_relations.json`
- `Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_rejected_relations.json`
- `Unified_Phosphorylation_Dataset/reports/rlims_p_v1_conversion_report.md`
- `Unified_Phosphorylation_Dataset/audit/brat/rlims_p_v1/*.ann`
- `Unified_Phosphorylation_Dataset/audit/brat/rlims_p_v1/*.txt`

Git ignore added:

- `.gitignore` ignores `.venv/`, `__pycache__/`, and `*.py[cod]`.

## How To Run The Actual NER Pipeline

From repository root:

```powershell
.\.venv\Scripts\python.exe Unified_Phosphorylation_Dataset\convert_rlims_p_v1_to_json.py
```

Last successful run output:

```text
Raw feature records: 89
Candidate relations: 30
Rejected records: 59

Candidate Confidence:
- high: 18
- medium: 8
- low: 4

Rejection Reasons:
- no_non_overlapping_kinase_substrate_pair: 54
- autophosphorylation_requires_manual_entity_choice: 5
```

A non-fatal spaCy `FutureWarning` may appear. The conversion still completes successfully.

## Why There Are 30 Candidates, Not 89

There are 89 RLIMS-P v1 phosphorylation feature records. The converter produces a candidate relation only when it can create a valid auditable pair:

- `[E1]` kinase/protein entity exists directly in the abstract text.
- `[E2]` substrate/protein entity exists directly in the abstract text.
- Both entity offsets match the source text exactly.
- Entities do not overlap.
- The pair passes conservative trigger, FT-line, NER, and dictionary heuristics.

The remaining 59 records are preserved in `rlims_p_v1_rejected_relations.json`, not discarded. They were rejected from automatic candidate output because:

- 54 records had no reliable non-overlapping kinase/substrate pair.
- 5 records were autophosphorylation and require manual entity-role choice.

This is intentional. The pipeline is conservative because bad automatic `[E1]`/`[E2]` markers would corrupt the unified dataset. These rejected records should be reviewed manually or handled by a second-stage manual-pairing workflow.

## Candidate Record Format

Candidate records are JSONL, one record per line, in:

```text
Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_candidate_relations.json
```

Important fields:

- `id` / `candidate_id`
- `source_record_id`
- `text`
- `text_with_entity_marker`
- `relation[0].entity_1`
- `relation[0].entity_1_idx`
- `relation[0].entity_1_idx_in_text_with_entity_marker`
- `relation[0].entity_2`
- `relation[0].entity_2_idx`
- `relation[0].entity_2_idx_in_text_with_entity_marker`
- `PMID`
- `PIR`
- `FT`
- `Kinase`
- `Substrate`
- `Site`
- `PPI`
- `Interactant`
- `ner_entities`
- `evidence_spans`
- `declared_kinase_text`
- `conversion_score`
- `conversion_confidence`
- `conversion_method`
- `requires_manual_audit`
- `source`

Every candidate has:

```json
"requires_manual_audit": true
```

Do not include these candidates in the final combined corpus until expert-approved.

## Quick Validation Command

Use this from repo root to verify output counts, marker counts, offsets, and BRAT file count:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from collections import Counter; base=Path(r'F:\document\QUT_research_assistant_file\Dr_Bashar_file\Phos_dataset\Unified_Phosphorylation_Dataset'); load=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]; raw=load(base/'data/processed/rlims_p_v1_raw_phosphorylation.json'); ner=load(base/'data/processed/rlims_p_v1_ner_candidates.json'); cand=load(base/'data/processed/rlims_p_v1_candidate_relations.json'); rej=load(base/'data/processed/rlims_p_v1_rejected_relations.json'); errors=[]; [errors.append((r.get('candidate_id'),'marker_count')) for r in cand if r.get('text_with_entity_marker','').count('[E1]')!=1 or r.get('text_with_entity_marker','').count('[/E1]')!=1 or r.get('text_with_entity_marker','').count('[E2]')!=1 or r.get('text_with_entity_marker','').count('[/E2]')!=1]; print('counts', {'raw':len(raw),'ner':len(ner),'candidates':len(cand),'rejected':len(rej)}); print('confidence', dict(Counter(r.get('conversion_confidence') for r in cand))); print('rejection_reasons', dict(Counter(r.get('rejection_reason') for r in rej))); print('marker_errors', len(errors)); print('brat_ann', len(list((base/'audit/brat/rlims_p_v1').glob('*.ann')))); print('brat_txt', len(list((base/'audit/brat/rlims_p_v1').glob('*.txt'))))"
```

Last validation result:

```text
counts {'raw': 89, 'ner': 89, 'candidates': 30, 'rejected': 59}
confidence {'high': 18, 'low': 4, 'medium': 8}
rejection_reasons {'no_non_overlapping_kinase_substrate_pair': 54, 'autophosphorylation_requires_manual_entity_choice': 5}
validation_errors 0
brat_ann 30
brat_txt 30
```

## Audit App

The Streamlit app now has two modes:

- `NER pipeline view (all 89 records)` - shows every RLIMS-P v1 record after NER, including NER spans, evidence spans, declared kinase, FT line, pipeline outcome, and whether the record became a strict candidate or was rejected.
- `Expert audit view (strict candidates)` - approval/rejection/revision workflow for the 30 strict `[E1]`/`[E2]` candidate relations.

The expert audit view is intentionally constrained. Reviewers no longer type entity text/start/end directly. They choose `P1` and `P2` from detected source-text spans. The app derives text/start/end from the selected span and only allows the reviewer to set the role. This prevents decisions with offsets that do not match the source text.

The audit app is separate from the NER converter. It should be used after candidate generation, when an expert is ready to inspect the pipeline or approve/reject/revise relation labels.

Install dependency if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install streamlit
```

Run from repository root:

```powershell
cd .\Unified_Phosphorylation_Dataset
..\.venv\Scripts\streamlit.exe run .\audit_rlims_p_v1_labels.py -- --candidates .\data\processed\rlims_p_v1_candidate_relations.json --ner .\data\processed\rlims_p_v1_ner_candidates.json --rejected .\data\processed\rlims_p_v1_rejected_relations.json --raw .\data\processed\rlims_p_v1_raw_phosphorylation.json --decisions .\data\audit\rlims_p_v1_label_decisions.jsonl
```

The app was last launched successfully at:

```text
http://localhost:8501
```

Audit decision output files:

- `Unified_Phosphorylation_Dataset/data/audit/rlims_p_v1_label_decisions.jsonl`
- `Unified_Phosphorylation_Dataset/data/audit/rlims_p_v1_label_decisions_latest.json`
- `Unified_Phosphorylation_Dataset/data/audit/rlims_p_v1_final_approved_relations.json`

A `0 approved` export is expected before expert labeling. It means no audit decisions have been saved yet; it does not mean the NER pipeline failed.

## Export Approved Records After Audit

Run after decisions exist:

```powershell
.\.venv\Scripts\python.exe Unified_Phosphorylation_Dataset\export_audited_rlims_p_v1.py
```

The export script should include only records with:

- `status == "approved"`
- `ppi_label == "phosphorylation"`

Do not add unaudited `rlims_p_v1` records to the final combined corpus.

## Design Decisions

1. JSONL is the source-of-truth audit format because it is append-only, versionable, reversible, and easy to diff.
2. BRAT export is useful for visual offset inspection, but not as the main decision store.
3. The converter and audit app are separate. The converter proposes candidates; the expert audit records truth.
4. `rlims_p_v1` does not provide a clean direct PPI label for every feature record. The FT line is phosphorylation-site evidence, not a complete relation label.
5. The automatic converter should prefer precision over recall because exact `[E1]` and `[E2]` offsets are required.
6. Autophosphorylation is not automatically converted because entity roles are ambiguous without expert confirmation.
7. The final unified dataset should only include expert-approved `rlims_p_v1` relations.

## Recommended Next Implementation Step

If the user wants all 89 records visible to experts, add a second review file rather than weakening the strict candidate rules:

```text
Unified_Phosphorylation_Dataset/data/processed/rlims_p_v1_needs_manual_pairing.json
```

This file should contain the 59 rejected records with:

- full abstract text
- FT line
- PMID/PIR/source record id
- phosphorylation site evidence
- all NER spans
- rejection reason
- suggested entity spans if available
- `requires_manual_pairing: true`

Then update the audit app to support two queues:

- `strict candidates` - current 30 automatic `[E1]`/`[E2]` relations.
- `manual pairing` - rejected records where the expert chooses or corrects `[E1]`/`[E2]` manually.

This keeps the data honest while allowing full coverage.

## Known Caveats

- Some low-confidence candidates are likely noisy and require expert review.
- The scispaCy model sometimes tags pronouns or broad phrases as gene/protein entities; heuristics filter some but not all of these.
- The local IPTMNet dictionary improves kinase/substrate role detection, but it is not perfect.
- `rg.exe` had access issues in this Windows environment earlier; use PowerShell commands if `rg` fails.
- Generated processed files are JSONL despite the `.json` extension.

## Do Not Do

- Do not treat the 30 candidate records as final ground truth.
- Do not export unaudited candidates into `combined_phosphorylation_corpus.json`.
- Do not overwrite audit decision history; append revisions with `supersedes_decision_id`.
- Do not relax the `[E1]`/`[E2]` offset checks unless adding a separate manual-pairing workflow.
