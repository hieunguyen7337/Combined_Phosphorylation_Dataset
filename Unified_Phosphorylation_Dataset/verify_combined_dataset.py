#!/usr/bin/env python3
"""Entry point for verifying the combined phosphorylation dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.config import COMBINED_DATASET_PATH, VERIFICATION_REPORT_PATH, ensure_project_directories
from phosphorylation_dataset.dataset_verifier import build_verification_report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the combined phosphorylation dataset.")
    parser.add_argument("--input", type=Path, default=COMBINED_DATASET_PATH, help="Combined dataset JSONL file.")
    parser.add_argument("--report", type=Path, default=VERIFICATION_REPORT_PATH, help="Markdown report output path.")
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    ensure_project_directories()

    if not args.input.exists():
        raise FileNotFoundError(f"Combined dataset not found: {args.input}")

    report_markdown = build_verification_report(args.input)
    args.report.write_text(report_markdown, encoding="utf-8")

    print(report_markdown)
    print(f"Saved verification report to {args.report.resolve()}")


if __name__ == "__main__":
    main()
