# Unified Phosphorylation Dataset Pipeline

This folder contains the code for building a unified phosphorylation-focused protein interaction dataset from multiple biomedical text-mining sources.

## Purpose

The code in this directory does three things:

1. Converts the `rlims_p_v2` BRAT annotations into a JSONL format that matches the eFIP-derived files.
2. Combines the normalized source files into one deduplicated dataset.
3. Verifies the final dataset and writes human-readable reports for quality checks.

The goal is to produce one training- or analysis-ready corpus where each record contains:

- the original text
- the same text with `[E1]...[/E1]` and `[E2]...[/E2]` entity markers
- normalized relation metadata
- phosphorylation-specific fields such as `Kinase`, `Substrate`, `Site`, and `PPI`

## Folder Layout

```text
Unified_Phosphorylation_Dataset/
|-- README.md
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
        |-- io_utils.py
        |-- rlims_conversion.py
        |-- dataset_combiner.py
        `-- dataset_verifier.py
```

## What Each Script Does

### `convert_rlims_to_efip.py`

Converts the RLIMS-P v2 BRAT annotations into the common JSONL schema.

Key behaviors:

- reads `.ann` and `.txt` pairs from `../rlims_p_v2`
- keeps only phosphorylation events
- requires both `Theme` and `Cause` protein arguments
- inserts `[E1]` and `[E2]` markers in textual order
- writes `data/processed/rlims_p_v2_converted.json`

### `combine_and_analyze_datasets.py`

Builds the final unified dataset from the normalized source files.

Key behaviors:

- loads the eFIP converted files and the RLIMS-P converted file
- fixes any entries where `E2` appears before `E1`
- deduplicates globally using `text_with_entity_marker`
- adds a `source` field to every accepted entry
- writes `data/processed/combined_phosphorylation_corpus.json`
- writes `reports/analysis_report.md`

### `verify_combined_dataset.py`

Checks that the final combined dataset looks consistent.

Key behaviors:

- confirms `text_with_entity_marker` is unique
- reports per-source text duplication counts
- reports relation-type distributions
- writes `reports/verification_report.md`

## How To Run

Run the commands from this folder:

```powershell
cd F:\document\QUT_research_assistant_file\Dr_Bashar_file\Phos_dataset\Unified_Phosphorylation_Dataset
python .\convert_rlims_to_efip.py
python .\combine_and_analyze_datasets.py
python .\verify_combined_dataset.py
```

You can also pass custom paths:

```powershell
python .\convert_rlims_to_efip.py --root ..\rlims_p_v2 --output .\data\processed\rlims_p_v2_converted.json
python .\combine_and_analyze_datasets.py --output .\data\processed\combined_phosphorylation_corpus.json --report .\reports\analysis_report.md
python .\verify_combined_dataset.py --input .\data\processed\combined_phosphorylation_corpus.json --report .\reports\verification_report.md
```

## Inputs And Outputs

### Inputs

- `../rlims_p_v2/`
- `data/processed/eFIP_corpus_converted.json`
- `data/processed/eFIP_full_converted.json`

### Outputs

- `data/processed/rlims_p_v2_converted.json`
- `data/processed/combined_phosphorylation_corpus.json`
- `reports/analysis_report.md`
- `reports/verification_report.md`

## Notes

- The pipeline uses only the Python standard library.
- The eFIP converted files are treated as already-normalized inputs.
- Deduplication is strict and is based on the full `text_with_entity_marker` string.
- The scripts are entrypoints; most of the logic now lives under `src/phosphorylation_dataset/` to keep the code easier to maintain.
