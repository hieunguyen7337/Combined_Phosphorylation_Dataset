#!/usr/bin/env python3
"""Export expert-approved RLIMS-P v1 decisions into unified JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.audit_labeling import export_approved_records, write_latest_decisions


DEFAULT_CANDIDATES = PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_candidate_relations.json"
DEFAULT_DECISIONS = PROJECT_ROOT / "data" / "audit" / "rlims_p_v1_label_decisions.jsonl"
DEFAULT_LATEST = PROJECT_ROOT / "data" / "audit" / "rlims_p_v1_label_decisions_latest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "audit" / "rlims_p_v1_final_approved_relations.json"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export audited RLIMS-P v1 candidate relations.")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--latest", type=Path, default=DEFAULT_LATEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    latest = write_latest_decisions(args.decisions, args.latest)
    records = export_approved_records(args.candidates, args.decisions, args.output)

    summary = {
        "latest_decisions": len(latest),
        "approved_phosphorylation_records": len(records),
        "latest_path": str(args.latest.resolve()),
        "output_path": str(args.output.resolve()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
