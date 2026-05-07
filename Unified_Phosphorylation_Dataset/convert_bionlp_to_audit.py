#!/usr/bin/env python3
"""Entry point for preparing BioNLP phosphorylation events for manual audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.bionlp_conversion import SourceSpec, convert_bionlp_for_audit
from phosphorylation_dataset.config import (
    BIONLP_AUDIT_CANDIDATES_PATH,
    BIONLP_AUDIT_REPORT_PATH,
    BIONLP_RAW_EVENTS_PATH,
    BIONLP_REJECTED_EVENTS_PATH,
    DEFAULT_BIONLP_2011_GE_ROOT,
    DEFAULT_BIONLP_2013_GE_ROOT,
    DEFAULT_BIONLP_EPI_ROOT,
    ensure_project_directories,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare BioNLP phosphorylation/dephosphorylation events for audit.")
    parser.add_argument("--epi-root", type=Path, default=DEFAULT_BIONLP_EPI_ROOT)
    parser.add_argument("--ge-2013-root", type=Path, default=DEFAULT_BIONLP_2013_GE_ROOT)
    parser.add_argument("--ge-2011-root", type=Path, default=DEFAULT_BIONLP_2011_GE_ROOT)
    parser.add_argument("--raw-output", type=Path, default=BIONLP_RAW_EVENTS_PATH)
    parser.add_argument("--candidate-output", type=Path, default=BIONLP_AUDIT_CANDIDATES_PATH)
    parser.add_argument("--rejected-output", type=Path, default=BIONLP_REJECTED_EVENTS_PATH)
    parser.add_argument("--report", type=Path, default=BIONLP_AUDIT_REPORT_PATH)
    parser.add_argument("--brat-output", type=Path, default=PROJECT_ROOT / "audit" / "brat" / "bionlp")
    parser.add_argument("--no-brat", action="store_true", help="Skip writing BRAT audit files.")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["epi_2011", "ge_2013", "ge_2011"],
        default=["epi_2011", "ge_2013", "ge_2011"],
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    ensure_project_directories()

    source_map = {
        "epi_2011": SourceSpec("bionlp_st_2011_epi", args.epi_root),
        "ge_2013": SourceSpec("bionlp_st_2013_ge", args.ge_2013_root),
        "ge_2011": SourceSpec("bionlp_st_2011_ge", args.ge_2011_root),
    }
    sources = [source_map[name] for name in args.sources]

    missing = [str(source.root) for source in sources if not source.root.exists()]
    if missing:
        raise FileNotFoundError(f"Missing BioNLP source root(s): {', '.join(missing)}")

    result = convert_bionlp_for_audit(
        sources=sources,
        raw_output=args.raw_output,
        candidate_output=args.candidate_output,
        rejected_output=args.rejected_output,
        report_path=args.report,
        brat_output=None if args.no_brat else args.brat_output,
    )

    print(result.report_markdown)
    print(f"Saved raw events to {args.raw_output.resolve()}")
    print(f"Saved audit candidates to {args.candidate_output.resolve()}")
    print(f"Saved rejected events to {args.rejected_output.resolve()}")
    print(f"Saved report to {args.report.resolve()}")
    if not args.no_brat:
        print(f"Saved BRAT audit files to {args.brat_output.resolve()}")


if __name__ == "__main__":
    main()
