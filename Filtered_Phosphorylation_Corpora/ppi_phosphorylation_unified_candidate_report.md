# PPI Phosphorylation Filter Unified Candidate Conversion

Filtered source sentences: 321
Sentences with annotated interactions: 205
Annotated interactions in filtered sentences: 420
Converted relation rows: 406
Source sentences represented after conversion: 205
Dropped interactions: 14

## Class Distribution

- PPI: 406

## Corpus Distribution

- BioInfer-train: 173
- AIMed-train: 73
- IEPA-train: 50
- BioInfer-test: 47
- AIMed-test: 21
- IEPA-test: 13
- LLL-train: 13
- HPRD50-test: 7
- HPRD50-train: 7
- LLL-test: 2

## Dropped Interaction Reasons

- unsupported_discontinuous_or_bad_offset: 14

## Quality Checks

- marker_and_offset_issues: 0

## Top Phosphorylation Terms

- phosphorylation: 130
- phosphoprotein: 61
- phosphorylated: 58
- phospholipase: 51
- phosphoinositides: 24
- phosphorylate: 21
- dephosphorylation: 16
- phosphorylates: 11
- phosphoinositide: 11
- phosphorylating: 6
- phosphoinositide-binding: 5
- phosphotyrosine-containing: 4
- phosphosphorylated: 3
- dephosphorylating: 3
- phosphotyrosines: 2

## Interpretation

These rows match the unified marker schema and preserve original PPI annotations, but they are not guaranteed phosphorylation-specific kinase-substrate relations. They should be treated as PPI-in-phosphorylation-context candidates or manually audited before mixing into the eFIP/RLIMS-P phosphorylation relation corpus.
