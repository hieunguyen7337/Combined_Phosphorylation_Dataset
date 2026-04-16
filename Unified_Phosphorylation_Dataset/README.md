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

What the code does not do today:

- convert `BioCreative_4/`
- convert `Text_mining_UDel/`
- use `rlims_p_v1/Phospho_Patterns.txt` in the current pipeline

So this folder should be understood as a pipeline for the current unified phosphorylation dataset build, not as a universal converter for every dataset archive in the repository.

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
