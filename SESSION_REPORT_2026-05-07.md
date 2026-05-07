# Session Report: Phosphorylation Corpus Expansion

Date: 2026-05-07

## What Changed

- Added BioNLP 2011/2013 event corpora as manual-audit sources, not training-ready relation data.
- Added a BioNLP audit converter:
  - `Unified_Phosphorylation_Dataset/convert_bionlp_to_audit.py`
  - `Unified_Phosphorylation_Dataset/src/phosphorylation_dataset/bionlp_conversion.py`
- Removed the stale idea that `bionlp_phosphorylation_events.json` should be treated as a PPI dataset. BioNLP now produces:
  - raw phosphorylation/dephosphorylation events
  - manual annotation candidates
  - BRAT audit files
  - an audit conversion report
- Downloaded additional candidate corpora:
  - BioNLP-ST 2009 GE
  - GENIA Meta-Knowledge
  - ProteinResidueRelations
  - AIMed/BioInfer/HPRD50/IEPA/LLL PPI bundle
  - BioRED
  - 1,000 raw PubMed phosphorylation abstracts
- Filtered auxiliary sources for phosphorylation-related records under `Filtered_Phosphorylation_Corpora/`.
- Converted phosphorylation-context PPI interactions into the unified marker format as candidates.

## Key Counts

BioNLP manual-audit conversion:

| Output | Count |
| --- | ---: |
| Raw phosphorylation/dephosphorylation events | 507 |
| Audit candidates | 507 |
| Candidates with explicit BioNLP Cause/Catalysis evidence | 8 |
| Rejected events | 0 |

Additional phosphorylation-filtered sources:

| Source | Filtered rows |
| --- | ---: |
| BioNLP-ST 2009 GE phosphorylation events | 216 |
| PPI corpus phosphorylation-context sentences | 321 |
| BioRED phosphorylation documents | 46 |
| GENIA Meta-Knowledge phosphorylation XML index rows | 146 |
| ProteinResidue phosphorylation annotation files | 140 |
| Raw PubMed phosphorylation abstracts | 1,000 |

PPI phosphorylation-context conversion:

| Metric | Count |
| --- | ---: |
| Phosphorylation-filtered PPI sentences | 321 |
| Sentences with annotated PPI | 205 |
| Annotated PPI interactions | 420 |
| Converted unified-format PPI rows | 406 |
| Dropped interactions | 14 |

The 406 converted rows are true PPI labels from the original PPI corpora, but they are not guaranteed phosphorylation-dependent interactions or kinase-substrate relations. They should be treated as `PPI in phosphorylation-context` candidates unless manually audited.

## Interpretation

- The current final relation corpus remains `combined_phosphorylation_corpus.json`, built from eFIP and RLIMS-P v2.
- RLIMS-P v1 and BioNLP are audit sources. They should not be merged into the final training corpus until reviewed.
- The PPI-filtered converted rows can be used immediately only for a broad label such as `PPI in a phosphorylation-context sentence`.
- They should not be used as confirmed phosphorylation-specific PPI, phosphorylation-dependent PPI, or kinase-substrate examples without manual audit or stricter rule-based validation.

## Main Artifacts

- `ADDITIONAL_CORPUS_SOURCES.md`
- `Filtered_Phosphorylation_Corpora/README.md`
- `Filtered_Phosphorylation_Corpora/ppi_phosphorylation_unified_candidate.jsonl`
- `Filtered_Phosphorylation_Corpora/ppi_phosphorylation_unified_candidate_report.md`
- `Unified_Phosphorylation_Dataset/data/processed/bionlp_annotation_candidates.json`
- `Unified_Phosphorylation_Dataset/reports/bionlp_audit_conversion_report.md`
