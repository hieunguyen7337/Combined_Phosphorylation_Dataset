#!/usr/bin/env python3
"""Entry point for converting raw eFIP spreadsheets into normalized JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.config import (
    EFIP_CORPUS_PATH,
    EFIP_FULL_PATH,
    EFIP_MULTI_SENT_SAMPLE_PATH,
    WORKSPACE_ROOT,
    ensure_project_directories,
)
from phosphorylation_dataset.efip_conversion import convert_efip_sources


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert raw eFIP spreadsheets into normalized JSONL files.")
    parser.add_argument(
        "--corpus-annotations",
        type=Path,
        default=WORKSPACE_ROOT / "eFIP" / "Corpus" / "Annotations.xlsx",
    )
    parser.add_argument(
        "--corpus-subsections",
        type=Path,
        default=WORKSPACE_ROOT / "eFIP" / "Corpus" / "Subsections",
    )
    parser.add_argument(
        "--full-input",
        type=Path,
        default=WORKSPACE_ROOT / "eFIP" / "eFIP.xlsx",
    )
    parser.add_argument("--corpus-output", type=Path, default=EFIP_CORPUS_PATH)
    parser.add_argument("--full-output", type=Path, default=EFIP_FULL_PATH)
    parser.add_argument("--multi-sentence-sample", type=Path, default=EFIP_MULTI_SENT_SAMPLE_PATH)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    ensure_project_directories()

    result = convert_efip_sources(
        corpus_annotations_path=args.corpus_annotations,
        corpus_subsections_dir=args.corpus_subsections,
        full_input_path=args.full_input,
        corpus_output_path=args.corpus_output,
        full_output_path=args.full_output,
        multi_sentence_sample_path=args.multi_sentence_sample,
    )

    print(
        "eFIP corpus: "
        f"input_rows={result.corpus_summary.input_rows} "
        f"output_rows={result.corpus_summary.output_rows} "
        f"skipped_rows={result.corpus_summary.skipped_rows} "
        f"unsupported_overlap_rows={result.corpus_summary.unsupported_overlap_rows} "
        f"unmatched_rows={result.corpus_summary.unmatched_rows}"
    )
    print(
        "eFIP full: "
        f"input_rows={result.full_summary.input_rows} "
        f"output_rows={result.full_summary.output_rows} "
        f"skipped_rows={result.full_summary.skipped_rows} "
        f"unsupported_overlap_rows={result.full_summary.unsupported_overlap_rows} "
        f"unmatched_rows={result.full_summary.unmatched_rows}"
    )
    print(f"Wrote corpus output to {args.corpus_output.resolve()}")
    print(f"Wrote full output to {args.full_output.resolve()}")
    print(f"Wrote multi-sentence sample to {args.multi_sentence_sample.resolve()}")


if __name__ == "__main__":
    main()
