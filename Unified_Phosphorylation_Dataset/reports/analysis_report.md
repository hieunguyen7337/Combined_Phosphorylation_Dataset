# Dataset Analysis: Combined PPI

**Total Unique Entries**: **1,282**

---

## Source Statistics & Relations

High-level overview of each source after strict deduplication by `text_with_entity_marker`.

| Source | Original Total | Accepted (Unique) | Duplicates Dropped | Top Relation Types |
| --- | --- | --- | --- | --- |
| **eFIP_corpus** | 355 | 330 | 25 | binding: 65, interaction: 58, interactions: 28, ... |
| **eFIP_full** | 66 | 65 | 1 | binding: 19, interaction: 16, association: 7, ... |
| **rlims_p_v2** | 1,375 | 887 | 488 | interaction: 887 |

> **Note**: Deduplication is global and applied sequentially across the source files.

---

## Entity Marker Patterns

The pattern below shows the order in which marked entities appear inside `text_with_entity_marker`.

| Pattern | Count | Sources |
| --- | --- | --- |
| `[E1] - [/E1] - [E2] - [/E2]` | 1,282 | eFIP_corpus, eFIP_full, rlims_p_v2 |

---

## Text & Linguistic Statistics

Comparison of word counts and sentence counts for accepted entries only.

| Source | Avg. Words | Range (Words) | Avg. Sents | Range (Sents) |
| --- | --- | --- | --- | --- |
| **eFIP_corpus** | 34.17 | 8 - 201 | 1.02 | 1 - 2 |
| **eFIP_full** | 25.25 | 7 - 52 | 1.00 | 1 - 1 |
| **rlims_p_v2** | 368.26 | 61 - 2592 | 13.71 | 3 - 107 |
| **OVERALL** | **264.87** | **7 - 2592** | **9.80** | **1 - 107** |
