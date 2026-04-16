#!/usr/bin/env python3
"""Entry point for combining normalized phosphorylation datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.config import (
    ANALYSIS_REPORT_PATH,
    COMBINED_DATASET_PATH,
    EFIP_CORPUS_PATH,
    EFIP_FULL_PATH,
    RLIMS_CONVERTED_PATH,
    ensure_project_directories,
)
from phosphorylation_dataset.dataset_combiner import combine_datasets


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Combine normalized phosphorylation datasets into one JSONL file.")
    parser.add_argument("--efip-corpus", type=Path, default=EFIP_CORPUS_PATH)
    parser.add_argument("--efip-full", type=Path, default=EFIP_FULL_PATH)
    parser.add_argument("--rlims", type=Path, default=RLIMS_CONVERTED_PATH)
    parser.add_argument("--output", type=Path, default=COMBINED_DATASET_PATH)
    parser.add_argument("--report", type=Path, default=ANALYSIS_REPORT_PATH)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    ensure_project_directories()

    input_files = {
        "eFIP_corpus": args.efip_corpus,
        "eFIP_full": args.efip_full,
        "rlims_p_v2": args.rlims,
    }
    missing = [str(path) for path in input_files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input file(s): {', '.join(missing)}")

    result = combine_datasets(input_files, args.output)
    args.report.write_text(result.report_markdown, encoding="utf-8")

    print(result.report_markdown)
    print(f"Saved combined dataset to {args.output.resolve()}")
    print(f"Saved analysis report to {args.report.resolve()}")


if __name__ == "__main__":
    main()
