# Unified Phosphorylation Dataset Pipeline

This folder contains the code for building a unified phosphorylation-focused protein interaction dataset from multiple biomedical text-mining sources.

## Run Order

Run the Python scripts in this order from this folder:

```powershell
cd F:\document\QUT_research_assistant_file\Dr_Bashar_file\Phos_dataset\Unified_Phosphorylation_Dataset
python .\convert_efip_to_json.py
python .\convert_rlims_to_efip.py
python .\combine_and_analyze_datasets.py
python .\verify_combined_dataset.py
```

Why this order matters:

1. `convert_efip_to_json.py`
   This must run first because it converts the original raw eFIP Excel files into the normalized JSONL files used by the rest of the pipeline. Without this step, there is no fresh [eFIP_corpus_converted.json](./data/processed/eFIP_corpus_converted.json) or [eFIP_full_converted.json](./data/processed/eFIP_full_converted.json) to merge.

2. `convert_rlims_to_efip.py`
   This runs second because it converts the raw [`rlims_p_v2`](../rlims_p_v2/) BRAT annotations into the same general JSONL structure used by the eFIP outputs. After this step, both major sources are available in a comparable normalized format.

3. `combine_and_analyze_datasets.py`
   This runs third because it depends on the outputs from both conversion steps. It merges the normalized eFIP and RLIMS-P files, fixes marker order when needed, removes duplicates, and writes the unified dataset plus the [analysis report](./reports/analysis_report.md).

4. `verify_combined_dataset.py`
   This runs last because it checks the final combined file created by the combine step. Its job is quality control: confirm marker uniqueness, summarize source statistics, and produce a [verification report](./reports/verification_report.md) for the final dataset.

If you skip or reorder these steps, later scripts may run on stale files, incomplete inputs, or missing outputs.

## Purpose

The code in this directory does three things:

1. Converts the `rlims_p_v2` BRAT annotations into a JSONL format that matches the eFIP-derived files.
2. Converts the raw eFIP spreadsheets into normalized JSONL files.
3. Combines the normalized source files into one deduplicated dataset.
4. Verifies the final dataset and writes human-readable reports for quality checks.

The goal is to produce one training- or analysis-ready corpus where each record contains:

- the original text
- the same text with `[E1]...[/E1]` and `[E2]...[/E2]` entity markers
- normalized relation metadata
- phosphorylation-specific fields such as `Kinase`, `Substrate`, `Site`, and `PPI`

## Scope Of The Current Code

The current code does not convert every dataset that exists in the parent repository.

What the code does today:

- converts raw eFIP spreadsheet sources from `../eFIP/`
- converts raw BRAT annotations from `../rlims_p_v2/`
- merges those normalized sources into one combined dataset
- generates markdown reports describing the merged output
- generates auditable NER-based candidate relations from `../rlims_p_v1/`
- provides a local Streamlit app for inspecting all `rlims_p_v1` NER records and labeling strict candidate relations

What the code does not do today:

- convert `BioCreative_4/`
- convert `Text_mining_UDel/`
- automatically merge unaudited `rlims_p_v1` candidates into the final combined corpus

So this folder should be understood as a pipeline for the current unified phosphorylation dataset build, not as a universal converter for every dataset archive in the repository.

### Why `rlims_p_v1` Requires Audit Before Merging

The `../rlims_p_v1/` folder now includes the upstream RLIMS-P v1 benchmarking files:

- `rlimsp_benchmarking_IR_set.txt`: phosphorylation information-retrieval benchmark with relevant and irrelevant abstracts.
- `rlimsp_benchmarking_IE_set.shtml`: phosphorylation information-extraction benchmark with tagged evidence snippets, PMIDs, PIR IDs, PIR feature lines, titles, and abstracts.
- `RLIMS-P_patterns.doc` and `Phospho_Patterns.txt`: rule/pattern references.

The IE benchmark is phosphorylation-relevant, but it does not consistently provide the information needed for the unified `[E1]...[/E1]` and `[E2]...[/E2]` relation format. Its PIR feature lines provide phosphorylation residue and protein sequence positions, for example site positions such as `Ser686`, but not direct character offsets for both protein entities in the abstract. Some feature lines also omit the kinase entirely or express it only indirectly.

For that reason, `rlims_p_v1` is processed by a separate NER-assisted candidate generator. The generator creates strict candidate relations only when it can place exact, non-overlapping `[E1]` and `[E2]` spans in the abstract text. These candidates are not ground truth until expert-approved.

## Expert Audit For `rlims_p_v1`

`rlims_p_v1` candidate relations must be reviewed before they are merged into the final training corpus. The audit workflow is append-only: every saved expert decision is written to JSONL, and revisions create a new decision that supersedes the previous one instead of editing history.

The important rule is that `rlims_p_v1` output is currently audit-ready, not training-ready. The NER pipeline proposes candidates; expert decisions decide which candidates become final relation records.

### Installation

Run these commands from the repository root:

```powershell
cd F:\document\QUT_research_assistant_file\Dr_Bashar_file\Phos_dataset
```

Create the virtual environment if it does not already exist:

```powershell
py -3.9 -m venv .venv
```

Install Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\Unified_Phosphorylation_Dataset\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r .\Unified_Phosphorylation_Dataset\requirements-ner.txt
```

The NER/audit workflow depends on:

- `spacy`
- `scispacy`
- `en_ner_bionlp13cg_md`
- `streamlit`

### Run The Actual NER Pipeline

Run this from the repository root:

```powershell
.\.venv\Scripts\python.exe Unified_Phosphorylation_Dataset\convert_rlims_p_v1_to_json.py
```

Equivalent command from inside this folder:

```powershell
cd .\Unified_Phosphorylation_Dataset
..\.venv\Scripts\python.exe .\convert_rlims_p_v1_to_json.py
```

This writes:

- `data/processed/rlims_p_v1_raw_phosphorylation.json`
- `data/processed/rlims_p_v1_ner_candidates.json`
- `data/processed/rlims_p_v1_candidate_relations.json`
- `data/processed/rlims_p_v1_rejected_relations.json`
- `reports/rlims_p_v1_conversion_report.md`
- `audit/brat/rlims_p_v1/`

The files use JSONL records even though the extension is `.json`.

### How The `rlims_p_v1` NER Pipeline Processes Text

The implementation is split between:

- `convert_rlims_p_v1_to_json.py`: command-line entrypoint.
- `src/phosphorylation_dataset/rlims_v1_conversion.py`: parser, NER, candidate selection, output writer.

Processing steps:

1. Parse the upstream RLIMS-P v1 information-extraction benchmark from `../rlims_p_v1/rlimsp_benchmarking_IE_set.shtml`.
2. Extract each phosphorylation feature record.
3. Preserve source metadata:
   - `PMID`
   - `PIR`
   - title
   - abstract text
   - full abstract text
   - PIR FT line
   - feature type
   - phosphorylation residue
   - phosphorylation site positions
   - declared kinase text when the FT line contains one
   - red evidence spans from the source HTML
   - source reference
4. Run biomedical NER with `en_ner_bionlp13cg_md`.
5. Keep detected gene/protein-like spans with exact character offsets.
6. Enrich entity spans with local dictionary information from `../Text_mining_UDel/iptmnet5.1.zip` where possible.
7. Assign a dictionary role to each entity:
   - `kinase`
   - `substrate`
   - `protein`
8. Parse the FT line for phosphorylation residue/site evidence, such as `Ser686` or `Thr308`.
9. Score possible kinase/substrate pairs using:
   - declared kinase text from the FT line
   - NER spans
   - dictionary role
   - phosphorylation trigger words
   - evidence-span proximity
   - source-text order and distance
10. Choose one strict candidate pair only if a reliable pair exists.
11. Require exact source-text offsets for both selected entities.
12. Require non-overlapping P1/P2 spans.
13. Insert `[E1]...[/E1]` and `[E2]...[/E2]` markers into the abstract.
14. Write successful strict candidates to `rlims_p_v1_candidate_relations.json`.
15. Write records that cannot be safely converted to `rlims_p_v1_rejected_relations.json`.
16. Write all NER-processed records to `rlims_p_v1_ner_candidates.json`.
17. Write BRAT `.ann` and `.txt` files for visual offset inspection.

Every strict candidate is marked:

```json
"requires_manual_audit": true
```

### Current `rlims_p_v1` NER Result

Last successful run:

```text
Raw feature records: 89
NER records: 89
Candidate relations: 30
Rejected records: 59
```

Candidate confidence:

```text
high: 18
medium: 8
low: 4
```

Rejected reasons:

```text
no_non_overlapping_kinase_substrate_pair: 54
autophosphorylation_requires_manual_entity_choice: 5
```

Validation result:

```text
validation_errors: 0
BRAT .ann files: 30
BRAT .txt files: 30
```

The 89 records are phosphorylation feature records, not all clean PPI relation records. The converter returns 30 strict candidates because it only creates a relation when it can safely produce this structure with exact source offsets:

```text
[E1]protein_or_kinase[/E1] ... [E2]protein_or_substrate[/E2]
```

The remaining 59 records are not discarded. They are preserved in `rlims_p_v1_rejected_relations.json` because automatic conversion was unsafe.

The main reasons are:

- Some FT lines describe phosphorylation sites but do not provide a clean kinase-substrate pair in the abstract.
- Some abstracts mention proteins, but not in a form where the converter can confidently assign P1/P2.
- Some NER spans are broad or noisy.
- Some records are autophosphorylation, where the same protein can act as both kinase and substrate.
- Exact direct positions are required for `[E1]` and `[E2]`; guessing would create bad training labels.

The current pipeline is therefore precision-first:

```text
30 = strict auditable candidate relations
59 = records needing manual pairing or rejected from strict automatic conversion
89 = total RLIMS-P v1 NER-processed records
```

### Run The Streamlit NER Viewer And Labeling App

Run the local app from the repository root:

```powershell
.\.venv\Scripts\streamlit.exe run Unified_Phosphorylation_Dataset\audit_rlims_p_v1_labels.py --server.port 8501 -- --candidates Unified_Phosphorylation_Dataset\data\processed\rlims_p_v1_candidate_relations.json --ner Unified_Phosphorylation_Dataset\data\processed\rlims_p_v1_ner_candidates.json --rejected Unified_Phosphorylation_Dataset\data\processed\rlims_p_v1_rejected_relations.json --raw Unified_Phosphorylation_Dataset\data\processed\rlims_p_v1_raw_phosphorylation.json --decisions Unified_Phosphorylation_Dataset\data\audit\rlims_p_v1_label_decisions.jsonl
```

Open:

```text
http://localhost:8501
```

The app has two modes:

- `NER pipeline view (all 89 records)`: shows every NER-processed RLIMS-P v1 record, including records rejected from strict candidate output.
- `Expert audit view (strict candidates)`: shows the 30 strict candidate relations for expert review.

The NER pipeline view is for understanding how the pipeline behaved. It shows:

- PMID and PIR
- title
- FT line
- declared kinase text
- phosphorylation site values
- evidence spans
- all NER spans
- dictionary roles
- whether the record became a strict candidate or was rejected
- rejection reason when applicable

The expert audit view is intentionally constrained. Reviewers no longer type entity text/start/end directly. They choose `P1` and `P2` from detected source-text spans. The app derives text/start/end from the selected span and only allows the reviewer to set the role. This prevents decisions with offsets that do not match the source text.

The app writes audit decisions to:

- `data/audit/rlims_p_v1_label_decisions.jsonl`
- `data/audit/rlims_p_v1_label_decisions_latest.json`

Before any expert labeling, approved records should be `0`. That is expected. It means no audit decisions have been saved yet; it does not mean the NER pipeline failed.

### Export Approved `rlims_p_v1` Relations

Export only expert-approved phosphorylation decisions:

```powershell
.\.venv\Scripts\python.exe Unified_Phosphorylation_Dataset\export_audited_rlims_p_v1.py --candidates Unified_Phosphorylation_Dataset\data\processed\rlims_p_v1_candidate_relations.json --decisions Unified_Phosphorylation_Dataset\data\audit\rlims_p_v1_label_decisions.jsonl --latest Unified_Phosphorylation_Dataset\data\audit\rlims_p_v1_label_decisions_latest.json --output Unified_Phosphorylation_Dataset\data\audit\rlims_p_v1_final_approved_relations.json
```

Only `approved` decisions with `ppi_label` set to `phosphorylation` are exported. Unreviewed or rejected candidates are not included in `combined_phosphorylation_corpus.json`.

If full 89-record label coverage is required, the next recommended change is to add a separate manual-pairing queue for the 59 rejected records. That should let experts pick P1/P2 from detected spans without weakening the strict automatic candidate rules.

## Folder Layout

```text
Unified_Phosphorylation_Dataset/
|-- README.md
|-- convert_efip_to_json.py
|-- convert_rlims_to_efip.py
|-- combine_and_analyze_datasets.py
|-- verify_combined_dataset.py
|-- data/
|   `-- processed/
|       |-- eFIP_corpus_converted.json
|       |-- eFIP_full_converted.json
|       |-- rlims_p_v2_converted.json
|       `-- combined_phosphorylation_corpus.json
|-- reports/
|   |-- analysis_report.md
|   `-- verification_report.md
`-- src/
    `-- phosphorylation_dataset/
        |-- __init__.py
        |-- config.py
        |-- efip_conversion.py
        |-- io_utils.py
        |-- rlims_conversion.py
        |-- dataset_combiner.py
        `-- dataset_verifier.py
```

## What Each Script Does

### `convert_efip_to_json.py`

Converts the original raw eFIP Excel sources into the normalized JSONL files used elsewhere in the pipeline.

Key behaviors:

- reads [../eFIP/Corpus/Annotations.xlsx](../eFIP/Corpus/Annotations.xlsx)
- reads the sentence lookup workbooks in [../eFIP/Corpus/Subsections/](../eFIP/Corpus/Subsections/)
- reads [../eFIP/eFIP.xlsx](../eFIP/eFIP.xlsx)
- resolves one or more source sentences for each annotation row
- performs case-insensitive entity matching and inserts `[E1]` and `[E2]` markers
- writes [data/processed/eFIP_corpus_converted.json](./data/processed/eFIP_corpus_converted.json)
- writes [data/processed/eFIP_full_converted.json](./data/processed/eFIP_full_converted.json)
- writes [data/processed/eFIP_multi_sent_sample.json](./data/processed/eFIP_multi_sent_sample.json)

### `convert_rlims_to_efip.py`

Converts the RLIMS-P v2 BRAT annotations into the common JSONL schema.

Key behaviors:

- reads `.ann` and `.txt` pairs from [../rlims_p_v2/](../rlims_p_v2/)
- keeps only phosphorylation events
- requires both `Theme` and `Cause` protein arguments
- inserts `[E1]` and `[E2]` markers in textual order
- writes [data/processed/rlims_p_v2_converted.json](./data/processed/rlims_p_v2_converted.json)

Important limitation:

- this script only converts `rlims_p_v2`
- it does not convert any other corpora stored elsewhere in the repository

### `combine_and_analyze_datasets.py`

Builds the final unified dataset from the normalized source files.

Key behaviors:

- loads the pre-existing eFIP converted files and the RLIMS-P converted file
- fixes any entries where `E2` appears before `E1`
- deduplicates globally using `text_with_entity_marker`
- adds a `source` field to every accepted entry
- writes [data/processed/combined_phosphorylation_corpus.json](./data/processed/combined_phosphorylation_corpus.json)
- writes [reports/analysis_report.md](./reports/analysis_report.md)

### `verify_combined_dataset.py`

Checks that the final combined dataset looks consistent.

Key behaviors:

- confirms `text_with_entity_marker` is unique
- reports per-source text duplication counts
- reports relation-type distributions
- writes [reports/verification_report.md](./reports/verification_report.md)

## Custom Paths

You can also pass custom paths:

```powershell
python .\convert_efip_to_json.py --corpus-annotations ..\eFIP\Corpus\Annotations.xlsx --corpus-subsections ..\eFIP\Corpus\Subsections --full-input ..\eFIP\eFIP.xlsx
python .\convert_rlims_to_efip.py --root ..\rlims_p_v2 --output .\data\processed\rlims_p_v2_converted.json
python .\combine_and_analyze_datasets.py --output .\data\processed\combined_phosphorylation_corpus.json --report .\reports\analysis_report.md
python .\verify_combined_dataset.py --input .\data\processed\combined_phosphorylation_corpus.json --report .\reports\verification_report.md
```

## Inputs And Outputs

### Inputs

- Raw eFIP sources:
- [../eFIP/Corpus/Annotations.xlsx](../eFIP/Corpus/Annotations.xlsx)
- [../eFIP/Corpus/Subsections/](../eFIP/Corpus/Subsections/)
- [../eFIP/eFIP.xlsx](../eFIP/eFIP.xlsx)
- Raw RLIMS-P annotation files from [../rlims_p_v2/](../rlims_p_v2/)

### Outputs

- [data/processed/rlims_p_v2_converted.json](./data/processed/rlims_p_v2_converted.json)
- [data/processed/eFIP_corpus_converted.json](./data/processed/eFIP_corpus_converted.json)
- [data/processed/eFIP_full_converted.json](./data/processed/eFIP_full_converted.json)
- [data/processed/eFIP_multi_sent_sample.json](./data/processed/eFIP_multi_sent_sample.json)
- [data/processed/combined_phosphorylation_corpus.json](./data/processed/combined_phosphorylation_corpus.json)
- [reports/analysis_report.md](./reports/analysis_report.md)
- [reports/verification_report.md](./reports/verification_report.md)

## Notes

- The RLIMS conversion uses only the Python standard library.
- The eFIP conversion depends on `openpyxl` for reading the raw Excel files.
- Deduplication is strict and is based on the full `text_with_entity_marker` string.
- The scripts are entrypoints; most of the logic now lives under `src/phosphorylation_dataset/` to keep the code easier to maintain.
- The current repository still does not convert every dataset archive in the parent workspace. `BioCreative_4/` and `Text_mining_UDel/` remain out of scope for the implemented pipeline.
