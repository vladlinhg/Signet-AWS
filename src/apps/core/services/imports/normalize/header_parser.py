import re
from typing import Dict, Optional, Any
from .utils import (
    DATE_MMDDYYYY_RE, DATE_MMM_D_YYYY_RE, TITLE_LANG_RE,
    iso_from_mmddyyyy, iso_from_mmm_d_yyyy
)

def parse_sales_user(text: str) -> Optional[str]:
    m = re.search(r"\b(?:Sales|Supera\s+Rep)\.?\s*[:：]\s*([a-zA-Z0-9_.-]+)\b", text, re.IGNORECASE)
    return m.group(1) if m else None

def parse_created_at(text: str) -> Optional[str]:
    m = re.search(r"\bCreated\s+at\s*[:：]?\s*(\d{2}/\d{2}/\d{4})\b", text, re.IGNORECASE)
    if m:
        mm, dd, yyyy = m.group(1).split("/")
        return iso_from_mmddyyyy(mm, dd, yyyy)
    m2 = DATE_MMDDYYYY_RE.search(text)
    if m2:
        return iso_from_mmddyyyy(m2.group(1), m2.group(2), m2.group(3))
    return None

def parse_group_no(text: str) -> Optional[int]:
    cleaned = re.sub(r"Update:\s*\([^)]+\)", "", text, flags=re.IGNORECASE)
    m = re.search(r"\bGroup\s*No\.?\s*[:：]?\s*(\d+)\b", cleaned, re.IGNORECASE | re.DOTALL)
    return int(m.group(1)) if m else None

def parse_currency(text: str) -> Optional[str]:
    m = re.search(r"\bCurrency\s*[:：]?\s*([A-Z]{3})\b", text, re.IGNORECASE)
    if m: return m.group(1).upper()
    return "CAD" if "CAD" in text else None

def parse_status(text: str) -> Optional[str]:
    t = text.lower()
    if "cancel" in t or "cxl" in t: return "CANCELLED"
    if "draft" in t: return "DRAFT"
    if "deposit" in t: return "DEPOSIT"
    if "paid" in t: return "PAID"
    if "invoiced" in t: return "INVOICED"
    return None

def parse_language(text: str) -> Optional[str]:
    m = TITLE_LANG_RE.search(text)
    if m: return m.group(1)
    m2 = re.search(r"\bTour\s+Language\s*[:：]?\s*(M|C|E)\b", text, re.IGNORECASE)
    return m2.group(1).upper() if m2 else None

def parse_tour_code(text: str) -> Optional[str]:
    m = re.search(r"\bTour\s+Code\s*[:：]?\s*([A-Z]{3}\d{5}[A-Z0-9]{1,3})\b", text, re.IGNORECASE)
    if m: return m.group(1).upper()
    m2 = re.search(r"\b([A-Z]{3}\d{5}[A-Z0-9]{1,3})\b", text)
    return m2.group(1).upper() if m2 else None

def parse_product_name(text: str, tour_code: Optional[str]) -> Optional[str]:
    if not tour_code:
        return None
    # Product name sits just before the tour code in the raw text stream usually
    # E.g. "Kanto + Kansai: Classics 10 days 8 nights JPN22917CE (R9/0, G0/0)"
    m = re.search(rf"([^\n\r]+?)\s+{re.escape(tour_code)}", text)
    if m:
        return m.group(1).strip()
    return None

def parse_product_from_tour_code(tour_code: str, tour_language: Optional[str]) -> Dict[str, str]:
    country = tour_code[:3]
    uniq8 = tour_code[8] if len(tour_code) > 8 else " "
    uniq9 = tour_code[9] if len(tour_code) > 9 else " "
    raw_unique = (uniq8 + uniq9).strip()

    if tour_language == "E" and tour_code.endswith("E"):
        if raw_unique.endswith("E") and len(raw_unique) >= 2:
            raw_unique = raw_unique[:-1].strip()

    if not raw_unique:
        raw_unique = uniq8.strip() or " "
    return {"country_code": country, "unique_seq": raw_unique}

def parse_dates_from_text(text: str) -> Dict[str, Optional[str]]:
    dates = []
    for m in DATE_MMDDYYYY_RE.finditer(text):
        dates.append(iso_from_mmddyyyy(m.group(1), m.group(2), m.group(3)))
    for m in DATE_MMM_D_YYYY_RE.finditer(text):
        iso = iso_from_mmm_d_yyyy(m.group(1), m.group(2), m.group(3))
        if iso: dates.append(iso)

    seen = set()
    ordered = [d for d in dates if not (d in seen or seen.add(d))]

    if len(ordered) >= 2:
        return {"start_date": ordered[0], "end_date": ordered[1]}
    if len(ordered) == 1:
        return {"start_date": ordered[0], "end_date": None}
    return {"start_date": None, "end_date": None}
