"""Project paths for the phosphorylation dataset pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_RLIMS_ROOT = WORKSPACE_ROOT / "rlims_p_v2"

EFIP_CORPUS_PATH = PROCESSED_DATA_DIR / "eFIP_corpus_converted.json"
EFIP_FULL_PATH = PROCESSED_DATA_DIR / "eFIP_full_converted.json"
RLIMS_CONVERTED_PATH = PROCESSED_DATA_DIR / "rlims_p_v2_converted.json"
COMBINED_DATASET_PATH = PROCESSED_DATA_DIR / "combined_phosphorylation_corpus.json"

ANALYSIS_REPORT_PATH = REPORTS_DIR / "analysis_report.md"
VERIFICATION_REPORT_PATH = REPORTS_DIR / "verification_report.md"


def ensure_project_directories() -> None:
    """Create the directories used by the refactored pipeline."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
