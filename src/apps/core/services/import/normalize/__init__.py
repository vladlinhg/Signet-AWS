import re
from pathlib import Path
from typing import Dict, Any
from .utils import load_json, find_all_text_blobs, BK_RE, BKRID_RE
from .main import normalize_booking_text

def group_text_by_booking(merged_obj: Any) -> Dict[str, str]:
    blobs = find_all_text_blobs(merged_obj)
    joined = "\n".join([b for b in blobs if b and len(b) > 0])

    matches = list(BK_RE.finditer(joined))
    if not matches:
        bkr_matches = list(BKRID_RE.finditer(joined))
        if not bkr_matches:
            return {}
        matches = bkr_matches

    booking_map: Dict[str, str] = {}
    for i, m in enumerate(matches):
        bk = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(joined)
        chunk = joined[start:end].strip()
        booking_map[bk] = chunk
    return booking_map

def extract_booking_texts_from_file(path: str | Path) -> Dict[str, str]:
    obj = load_json(path)
    booking_map = group_text_by_booking(obj)
    if booking_map:
        return booking_map

    # Fallback: whole doc as one blob, bk from filename
    bk_guess = re.findall(r"\d{5,6}", Path(path).stem)
    bk = bk_guess[0] if bk_guess else "UNKNOWN"
    blobs = find_all_text_blobs(obj)
    joined = "\n".join([b for b in blobs if b])
    return {bk: joined}

__all__ = ['normalize_booking_text', 'extract_booking_texts_from_file']
