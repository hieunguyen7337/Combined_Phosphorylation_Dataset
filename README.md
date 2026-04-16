# Phosphorylation Dataset Workspace

This repository is a biomedical text-mining workspace centered on phosphorylation-related corpora and dataset preparation.

## Main Idea

Most folders contain raw or archived source datasets. The active dataset-building code lives in:

- [Unified_Phosphorylation_Dataset](/F:/document/QUT_research_assistant_file/Dr_Bashar_file/Phos_dataset/Unified_Phosphorylation_Dataset)

That pipeline:

1. converts RLIMS-P v2 annotations into a shared JSONL schema
2. combines them with eFIP-derived normalized files
3. deduplicates and analyzes the merged dataset
4. verifies the final output

## Repository Overview

- `BioCreative_4/`: archived corpus files
- `eFIP/`: eFIP corpus source material and spreadsheets
- `rlims_p_v1/`: older rule/pattern resource
- `rlims_p_v2/`: RLIMS-P v2 annotations used by the converter
- `Text_mining_UDel/`: archived IPTMNet-related data
- `Unified_Phosphorylation_Dataset/`: refactored code, processed outputs, and reports

## Where To Start

Open the detailed pipeline guide here:

- [Unified_Phosphorylation_Dataset/README.md](/F:/document/QUT_research_assistant_file/Dr_Bashar_file/Phos_dataset/Unified_Phosphorylation_Dataset/README.md)
