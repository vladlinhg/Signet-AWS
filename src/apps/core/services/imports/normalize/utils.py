import re
import json
from pathlib import Path
from typing import Any, List, Optional

# ----------------------------
# Regex helpers / constants
# ----------------------------
BK_RE = re.compile(r"\b(?:SIG_CAN|SUP_CAN)\s+(\d{5,6})\b")
BKRID_RE = re.compile(r"[?&]bkrId=(\d{5,6})\b", re.IGNORECASE)
DATE_MMDDYYYY_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
DATE_MMM_D_YYYY_RE = re.compile(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b")
TITLE_LANG_RE = re.compile(r"\((M|C|E)\)")
NAME_COMMA_RE = re.compile(r"^\s*([^,]+)\s*,\s*(.+?)\s*$")
NA_RE = re.compile(r"^\s*(?:N/?A|NA|-)\s*$", re.IGNORECASE)

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

# Special month encoding in tour code
TOUR_MONTH_CODE = {**{str(i): i for i in range(1, 10)}, "A": 10, "B": 11, "C": 12}

# ----------------------------
# Shared Utilities
# ----------------------------
def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def iso_from_mmddyyyy(mm: str, dd: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"

def iso_from_mmm_d_yyyy(mmm: str, d: str, yyyy: str) -> Optional[str]:
    m = MONTH_MAP.get(mmm.strip().upper())
    if not m:
        return None
    return f"{yyyy}-{m:02d}-{int(d):02d}"

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def safe_lower(s: Optional[str]) -> Optional[str]:
    return s.lower() if s else None

def is_na(s: Optional[str]) -> bool:
    if s is None:
        return True
    return bool(NA_RE.match(s.strip()))

def find_all_text_blobs(obj: Any) -> List[str]:
    """Recursively collect all strings from a JSON-like object."""
    out: List[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, list):
        for x in obj:
            out.extend(find_all_text_blobs(x))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(find_all_text_blobs(k))
            out.extend(find_all_text_blobs(v))
    return out
