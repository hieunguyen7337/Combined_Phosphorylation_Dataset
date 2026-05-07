# Additional Corpus Sources Downloaded

Downloaded on 2026-05-07.

These folders are kept separate from `Unified_Phosphorylation_Dataset/data/processed/combined_phosphorylation_corpus.json`. They should be inspected and converted deliberately before any use in training.

## Phosphorylation/Event-Focused Sources

### `BioNLP_ST_2009_GE/`

- Source: BioNLP'09 Shared Task on Event Extraction, GENIA event extraction task.
- Download base: `http://www.nactem.ac.uk/GENIA/current/Shared-tasks/BioNLP-ST-2009/`
- Files downloaded:
  - `bionlp09_shared_task_training_data_rev2.tar.gz`
  - `bionlp09_shared_task_development_data_rev1.tar.gz`
  - `bionlp09_shared_task_test_data_without_gold_annotation.tar.gz`
- Local contents: 1,210 `.txt`, 1,210 `.a1`, 950 `.a2`.
- Quick scan: 216 annotated `Phosphorylation` event lines across 81 `.a2` files.
- Best use: phosphorylation trigger/substrate event audit source, similar to the existing BioNLP audit workflow.

### `GENIA_MetaKnowledge/`

- Source: NaCTeM GENIA event corpus enriched with meta-knowledge annotation.
- Download: `https://www.nactem.ac.uk/meta-knowledge/Meta-knowledge_GENIA_corpus.zip`
- Local contents: 2,000 XML files plus ontology/licence/support files.
- Quick scan: 125 XML files contain phosphorylation-related terms.
- Best use: XML-based GENIA event mining and meta-knowledge analysis. Requires a separate XML converter.

### `ProteinResidueRelations/`

- Source: BioNLP-Corpora ProteinResidue relations.
- Download: `https://master.dl.sourceforge.net/project/bionlp-corpora/ProteinResidue/ProteinResidueRelationsSilverCorpus_A1.tar.gz?viasf=1`
- Local contents: 973 `.a1` files.
- Quick scan: 58 files contain phosphorylation-related terms.
- Best use: protein-residue/site annotation support. This is a silver-standard protein-residue relation source, not a kinase-substrate PPI corpus.

### `PubMed_Phosphorylation_Raw/`

- Source: NCBI PubMed E-utilities query.
- Local output: `phosphorylation_pubmed_abstracts.jsonl`
- Query saved in: `query.txt`
- Current size: 1,000 abstracts with abstracts present.
- Best use: unannotated phosphorylation text for PubTator/RLIMS-P pre-annotation and later manual review.

## Broader PPI/Relation Sources

### `PPI_Corpora_metalrt/`

- Source: `https://github.com/metalrt/ppi-dataset`
- Local contents: AIMed, BioInfer, HPRD50, IEPA, and LLL split files in XML plus CSV outputs.
- Quick XML scan:
  - AIMed: 1,943 sentences, 991 interactions.
  - BioInfer: 1,100 sentences, 2,534 interactions.
  - HPRD50: 145 sentences, 163 interactions.
  - IEPA: 486 sentences, 335 interactions.
  - LLL: 77 sentences, 164 interactions.
- Best use: general PPI relation pretraining or negative-sampling experiments. It is not phosphorylation-specific.

### `BioRED/`

- Source: NCBI BioRED.
- Download: `https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/BIORED.zip`
- Local contents: BioC JSON, BioC XML, and PubTator files.
- Quick scan: 9 files contain phosphorylation-related terms.
- Best use: broad biomedical relation extraction with gene/protein entities. Useful as general RE/NER context, not as a phosphorylation-specific relation corpus.

## Current Recommendation

- Treat `BioNLP_ST_2009_GE/` as the next best phosphorylation-specific audit source.
- Treat `GENIA_MetaKnowledge/` as a richer but higher-effort XML source.
- Use `PPI_Corpora_metalrt/` only for general PPI pretraining or controlled comparison, because its distribution and labels differ from RLIMS-P/eFIP.
- Use `PubMed_Phosphorylation_Raw/` for pre-annotation, not supervised training.
