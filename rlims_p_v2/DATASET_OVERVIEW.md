# RLIMS-P v2 dataset overview

## Directory structure

The dataset is organized by curator (`curator_1`, `curator_2`) and annotation format (`brat`, `bioc`):

- `curator_{1,2}/brat/abstract/`
- `curator_{1,2}/brat/full_text/`
- `curator_{1,2}/bioc/abstract.xml`
- `curator_{1,2}/bioc/full_text.xml`

In BRAT folders, each PMID has paired files:

- `PMIDxxxxxx.txt` (title + abstract text)
- `PMIDxxxxxx.ann` (entity/event annotations)

## Corpus size and pairing

For **both** curators:

- `abstract`: 150 `.txt` + 150 `.ann` (all paired)
- `full_text`: 308 `.txt` + 308 `.ann` (all paired)
- PMID sets are identical between curators for each split.

## BRAT annotation content

Observed entity types in `.ann` files:

- `Protein`
- `Phosphorylation`
- `Site`
- `Anaphora` (only in abstract split)

Observed event type:

- `Phosphorylation` (with roles `Theme`, optional `Cause`, optional `Site`)

### Example BRAT records

Entity lines (`T*`):

```text
T14\tSite 859 869\tserine 931
T15\tPhosphorylation 873 887\tphosphorylated
T17\tProtein 1030 1032\tFu
```

Event lines (`E*`):

```text
E1\tPhosphorylation:T1 Theme:T2
E7\tPhosphorylation:T16 Theme:T9 Cause:T8 Site:T10
```

## BioC XML content

Each BioC file is a single `<collection>` with multiple `<document>` entries (one per PMID), and each document contains:

- `<text>` with title/abstract content
- `<annotation>` entries (converted entity mentions)
- `<relation>` entries representing phosphorylation events with role nodes (`Trigger`, `Theme`, optional `Cause`/`Site`)

Document counts:

- `abstract.xml`: 150 documents
- `full_text.xml`: 308 documents

## Curator-level annotation density snapshot

### curator_1

- Abstract BRAT entities: `Protein` 1185, `Phosphorylation` 1171, `Site` 436, `Anaphora` 38
- Abstract phosphorylation events: 1336
- Full-text BRAT entities: `Phosphorylation` 617, `Protein` 559, `Site` 142
- Full-text phosphorylation events: 586

### curator_2

- Abstract BRAT entities: `Protein` 1306, `Phosphorylation` 1195, `Site` 545, `Anaphora` 60
- Abstract phosphorylation events: 1564
- Full-text BRAT entities: `Phosphorylation` 434, `Protein` 388, `Site` 139
- Full-text phosphorylation events: 430

## Practical interpretation

- The repository contains two independent curator annotation sets over the same PMIDs.
- The task focus is phosphorylation event extraction around proteins/sites.
- BRAT is the source-like human-editable format; BioC is a structured XML export of comparable content.
