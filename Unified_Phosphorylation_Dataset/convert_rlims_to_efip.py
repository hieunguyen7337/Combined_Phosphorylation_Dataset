#!/usr/bin/env python3
"""Entry point for converting RLIMS-P v2 into the unified JSONL schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.config import DEFAULT_RLIMS_ROOT, RLIMS_CONVERTED_PATH, ensure_project_directories
from phosphorylation_dataset.rlims_conversion import convert_dataset


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert RLIMS-P v2 BRAT annotations to JSONL.")
    parser.add_argument("--root", type=Path, default=DEFAULT_RLIMS_ROOT, help="Path to the rlims_p_v2 folder.")
    parser.add_argument("--curators", nargs="+", default=["curator_1", "curator_2"])
    parser.add_argument("--splits", nargs="+", default=["abstract", "full_text"])
    parser.add_argument(
        "--output",
        type=Path,
        default=RLIMS_CONVERTED_PATH,
        help="Output JSONL path for the converted RLIMS-P data.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    ensure_project_directories()

    result = convert_dataset(
        root=args.root,
        curators=args.curators,
        splits=args.splits,
        output_path=args.output,
    )

    for split_name, stats in result.stats_by_split.items():
        print(
            f"{split_name}: total_events={stats.total_events} "
            f"kept={stats.kept} dropped={stats.dropped}"
        )

    print(
        f"Wrote {len(result.rows)} rows to {args.output}. "
        f"total_events={result.aggregate.total_events} "
        f"kept={result.aggregate.kept} dropped={result.aggregate.dropped}"
    )


if __name__ == "__main__":
    main()
