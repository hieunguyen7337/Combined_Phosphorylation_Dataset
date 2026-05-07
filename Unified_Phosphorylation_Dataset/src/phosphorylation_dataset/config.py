"""Project paths for the phosphorylation dataset pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_RLIMS_ROOT = WORKSPACE_ROOT / "rlims_p_v2"
DEFAULT_BIONLP_EPI_ROOT = WORKSPACE_ROOT / "BioNLP_ST_2011_EPI"
DEFAULT_BIONLP_2013_GE_ROOT = WORKSPACE_ROOT / "BioNLP_ST_2013_GE"
DEFAULT_BIONLP_2011_GE_ROOT = WORKSPACE_ROOT / "BioNLP_ST_2011_GE"

EFIP_CORPUS_PATH = PROCESSED_DATA_DIR / "eFIP_corpus_converted.json"
EFIP_FULL_PATH = PROCESSED_DATA_DIR / "eFIP_full_converted.json"
EFIP_MULTI_SENT_SAMPLE_PATH = PROCESSED_DATA_DIR / "eFIP_multi_sent_sample.json"
RLIMS_CONVERTED_PATH = PROCESSED_DATA_DIR / "rlims_p_v2_converted.json"
BIONLP_RAW_EVENTS_PATH = PROCESSED_DATA_DIR / "bionlp_raw_phosphorylation_events.json"
BIONLP_AUDIT_CANDIDATES_PATH = PROCESSED_DATA_DIR / "bionlp_annotation_candidates.json"
BIONLP_REJECTED_EVENTS_PATH = PROCESSED_DATA_DIR / "bionlp_rejected_events.json"
COMBINED_DATASET_PATH = PROCESSED_DATA_DIR / "combined_phosphorylation_corpus.json"

ANALYSIS_REPORT_PATH = REPORTS_DIR / "analysis_report.md"
VERIFICATION_REPORT_PATH = REPORTS_DIR / "verification_report.md"
BIONLP_AUDIT_REPORT_PATH = REPORTS_DIR / "bionlp_audit_conversion_report.md"


def ensure_project_directories() -> None:
    """Create the directories used by the refactored pipeline."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
