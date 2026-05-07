# Phosphorylation Dataset Workspace

This repository is a biomedical text-mining workspace centered on phosphorylation-related corpora and dataset preparation.

## Main Idea

Most folders contain raw or archived source datasets. The active dataset-building code lives in:

- [Unified_Phosphorylation_Dataset](./Unified_Phosphorylation_Dataset/)

That pipeline:

1. converts RLIMS-P v2 annotations into a shared JSONL schema
2. combines them with eFIP-derived normalized files
3. deduplicates and analyzes the merged dataset
4. verifies the final output
5. generates separate manual-audit sources for RLIMS-P v1 and BioNLP before any expert-approved export

## Repository Overview

- `BioCreative_4/`: archived corpus files
- `BioNLP_ST_2011_EPI/`: BioNLP-ST 2011 EPI standoff corpus, prepared as a manual-audit source
- `BioNLP_ST_2011_GE/`: BioNLP-ST 2011 GE standoff corpus, prepared as a manual-audit source
- `BioNLP_ST_2009_GE/`: BioNLP-ST 2009 GE standoff corpus, downloaded as an additional phosphorylation event source
- `BioNLP_ST_2013_GE/`: BioNLP-ST 2013 GE standoff corpus, prepared as a manual-audit source
- `BioRED/`: broad biomedical relation corpus with gene/protein entities
- `eFIP/`: eFIP corpus source material and spreadsheets
- `GENIA_MetaKnowledge/`: GENIA event corpus XML enriched with meta-knowledge annotation
- `PPI_Corpora_metalrt/`: AIMed, BioInfer, HPRD50, IEPA, and LLL PPI corpus bundle
- `ProteinResidueRelations/`: protein-residue relation corpus, useful for site/residue annotation support
- `PubMed_Phosphorylation_Raw/`: unannotated phosphorylation-focused PubMed abstract sample
- `rlims_p_v1/`: RLIMS-P v1 benchmarking files and older rule/pattern resource
- `rlims_p_v2/`: RLIMS-P v2 annotations used by the converter
- `Text_mining_UDel/`: archived IPTMNet-related data
- `Unified_Phosphorylation_Dataset/`: refactored code, processed outputs, and reports

## Where To Start

Open the detailed pipeline guide here:

- [Unified_Phosphorylation_Dataset/README.md](./Unified_Phosphorylation_Dataset/README.md)
- [ADDITIONAL_CORPUS_SOURCES.md](./ADDITIONAL_CORPUS_SOURCES.md)
- [SESSION_REPORT_2026-05-07.md](./SESSION_REPORT_2026-05-07.md)

That README also documents the RLIMS-P v1 NER workflow, the BioNLP manual-audit workflow, installation commands, Streamlit inspection/labeling app, current run results, and why unaudited candidates are kept out of the final corpus.

## Source Dataset Download Links

The repository contains a mix of active inputs, archived corpora, and reference exports. The original upstream download links are:

- `eFIP/`
  - Upstream dataset page:
    - [https://research.bioinformatics.udel.edu/iprolink/corpora.php](https://research.bioinformatics.udel.edu/iprolink/corpora.php)
  - Direct download links:
    - Full-length corpus ZIP (matches `eFIP/Corpus/` source material):
      - [https://research.bioinformatics.udel.edu/eFIPonline/Corpus.zip](https://research.bioinformatics.udel.edu/eFIPonline/Corpus.zip)
    - Other corpus spreadsheet:
      - [https://pir.georgetown.edu/pirwww/iprolink/eFIP.xlsx](https://pir.georgetown.edu/pirwww/iprolink/eFIP.xlsx)

- `rlims_p_v2/`
  - Upstream dataset page:
    - [https://research.bioinformatics.udel.edu/iprolink/corpora.php](https://research.bioinformatics.udel.edu/iprolink/corpora.php)
  - Direct download link:
    - RLIMS-P v2 corpus TAR.GZ:
      - [https://research.bioinformatics.udel.edu/text_mining/corpus/tars/rlims2.tar.gz](https://research.bioinformatics.udel.edu/text_mining/corpus/tars/rlims2.tar.gz)

- `rlims_p_v1/`
  - Upstream dataset page:
    - [https://research.bioinformatics.udel.edu/iprolink/corpora.php](https://research.bioinformatics.udel.edu/iprolink/corpora.php)
  - Direct download links:
    - Phosphorylation information-retrieval benchmark dataset:
      - [https://proteininformationresource.org/iprolink/rlimsp_benchmarking_IR_set](https://proteininformationresource.org/iprolink/rlimsp_benchmarking_IR_set)
    - Phosphorylation information-extraction benchmark dataset:
      - [https://proteininformationresource.org/iprolink/rlimsp_benchmarking_IE_set.shtml](https://proteininformationresource.org/iprolink/rlimsp_benchmarking_IE_set.shtml)
    - RLIMS-P phospho patterns:
      - [https://proteininformationresource.org/iprolink/RLIMS-P_patterns.doc](https://proteininformationresource.org/iprolink/RLIMS-P_patterns.doc)
  - Note:
    - The information-extraction benchmark has tagged phosphorylation evidence and PIR feature lines, but it does not consistently provide direct character offsets for both phosphorylation substrate and kinase protein mentions. It is therefore not directly equivalent to the `Unified_Phosphorylation_Dataset` relation-marker format without heuristic extraction or manual curation.

- `Text_mining_UDel/`
  - Upstream export index:
    - [https://hershey.dbi.udel.edu/textmining/export](https://hershey.dbi.udel.edu/textmining/export)
  - Direct download link:
    - IPTMNet export ZIP:
      - [https://hershey.dbi.udel.edu/textmining/export/iptmnet5.1.zip](https://hershey.dbi.udel.edu/textmining/export/iptmnet5.1.zip)

- `BioCreative_4/`
  - Upstream dataset index:
    - [https://ftp.ncbi.nlm.nih.gov/pub/lu/BC4GO/](https://ftp.ncbi.nlm.nih.gov/pub/lu/BC4GO/)
  - Direct download link:
    - BioCreative IV Task 4 corpus ZIP:
      - [https://ftp.ncbi.nlm.nih.gov/pub/lu/BC4GO/bc4go_test_v090313_.zip](https://ftp.ncbi.nlm.nih.gov/pub/lu/BC4GO/bc4go_test_v090313_.zip)

- `BioNLP_ST_2011_EPI/`
  - Upstream task page:
    - [https://2011.bionlp-st.org/bionlp-shared-task-2011/epigenetics-and-post-translational-modifications-task-epi](https://2011.bionlp-st.org/bionlp-shared-task-2011/epigenetics-and-post-translational-modifications-task-epi)
  - Downloaded mirror:
    - [https://github.com/openbiocorpora/bionlp-st-2011-epi/archive/refs/heads/master.zip](https://github.com/openbiocorpora/bionlp-st-2011-epi/archive/refs/heads/master.zip)

- `BioNLP_ST_2013_GE/`
  - Reference dataset page:
    - [https://huggingface.co/datasets/bigbio/bionlp_st_2013_ge](https://huggingface.co/datasets/bigbio/bionlp_st_2013_ge)
  - Downloaded mirror:
    - [https://github.com/openbiocorpora/bionlp-st-2013-ge/archive/refs/heads/master.zip](https://github.com/openbiocorpora/bionlp-st-2013-ge/archive/refs/heads/master.zip)

- `BioNLP_ST_2011_GE/`
  - Upstream downloads:
    - [https://bionlp-st.dbcls.jp/GE/2011/downloads/](https://bionlp-st.dbcls.jp/GE/2011/downloads/)
  - Direct downloads used:
    - [https://bionlp-st.dbcls.jp/GE/2011/downloads/BioNLP-ST_2011_genia_train_data_rev1.tar.gz](https://bionlp-st.dbcls.jp/GE/2011/downloads/BioNLP-ST_2011_genia_train_data_rev1.tar.gz)
    - [https://bionlp-st.dbcls.jp/GE/2011/downloads/BioNLP-ST_2011_genia_devel_data_rev1.tar.gz](https://bionlp-st.dbcls.jp/GE/2011/downloads/BioNLP-ST_2011_genia_devel_data_rev1.tar.gz)

## Notes on Provenance

- The `eFIP/` and `rlims_p_v2/` folders correspond to corpora listed on the iProLINK corpora page.
- The `Text_mining_UDel/` folder appears to correspond more closely to files exposed from the UDel text-mining export index, especially IPTMNet and RLIMS JSON exports.
- `BioCreative_4/` is an archived corpus is not part of the current conversion pipeline.
- The BioNLP folders are not merged into the final relation corpus. They are converted into raw event records and manual-audit candidates because BioNLP event annotations usually do not provide complete kinase-substrate/PPI labels.
