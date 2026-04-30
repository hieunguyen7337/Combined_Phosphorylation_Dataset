#!/usr/bin/env python3
"""Entry point for generating auditable RLIMS-P v1 NER candidates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phosphorylation_dataset.rlims_v1_conversion import convert_rlims_v1


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert RLIMS-P v1 IE records into auditable NER candidates.")
    parser.add_argument("--input", type=Path, default=WORKSPACE_ROOT / "rlims_p_v1" / "rlimsp_benchmarking_IE_set.shtml")
    parser.add_argument("--iptmnet-zip", type=Path, default=WORKSPACE_ROOT / "Text_mining_UDel" / "iptmnet5.1.zip")
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_raw_phosphorylation.json",
    )
    parser.add_argument(
        "--ner-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_ner_candidates.json",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_candidate_relations.json",
    )
    parser.add_argument(
        "--rejected-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "rlims_p_v1_rejected_relations.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "reports" / "rlims_p_v1_conversion_report.md",
    )
    parser.add_argument(
        "--brat-output",
        type=Path,
        default=PROJECT_ROOT / "audit" / "brat" / "rlims_p_v1",
    )
    parser.add_argument("--model", default="en_ner_bionlp13cg_md")
    parser.add_argument("--no-brat", action="store_true", help="Skip writing BRAT audit files.")
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    result = convert_rlims_v1(
        input_path=args.input,
        iptmnet_zip=args.iptmnet_zip,
        raw_output=args.raw_output,
        ner_output=args.ner_output,
        candidate_output=args.candidate_output,
        rejected_output=args.rejected_output,
        report_path=args.report,
        brat_output=None if args.no_brat else args.brat_output,
        model_name=args.model,
    )
    print(result.report_markdown)
    print(f"Saved raw records to {args.raw_output.resolve()}")
    print(f"Saved NER records to {args.ner_output.resolve()}")
    print(f"Saved candidate relations to {args.candidate_output.resolve()}")
    print(f"Saved rejected records to {args.rejected_output.resolve()}")
    print(f"Saved report to {args.report.resolve()}")
    if not args.no_brat:
        print(f"Saved BRAT audit files to {args.brat_output.resolve()}")


if __name__ == "__main__":
    main()
