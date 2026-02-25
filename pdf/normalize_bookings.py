"""
normalize_bookings.py

Purpose
- Normalize extracted PDF text JSON(s) into DB-schema-friendly "normalized JSON"
- Supports:
  1) single booking extract JSON (e.g., 344565.json)
  2) merged/combined JSON with multiple booking blocks containing "SIG_CAN XXXXX" or "SUP_CAN XXXXX"

Key outputs per booking:
- invoice
- sales user + agent profile (internal rep) vs external placeholder agent
- agency + address (separate table)
- clients (lookup_key uses first,last,dob,gender)
- travel documents (skip if N/A)
- tour instance / product (no airport fields stored on tour instance)
- invoice items (qty + unit_price only; totals are computed for integrity check)
- invoice notes (header notes + log history + record-only info)
- payments (with mapping)
- integrity checks + notifications (append-only; no overwrite)

This script is extraction/normalization-layer only.
DB upsert/lookup happens in your importer; we emit "plans" + notifications.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------
# Regex helpers / constants
# ----------------------------

BK_RE = re.compile(r"\b(?:SIG_CAN|SUP_CAN)\s+(\d{5,6})\b")

# Booking URL forms sometimes include bkrId=XXXXX
BKRID_RE = re.compile(r"[?&]bkrId=(\d{5,6})\b", re.IGNORECASE)

DATE_MMDDYYYY_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
DATE_MMM_D_YYYY_RE = re.compile(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b")  # e.g. Apr 7 1953

TIME_AMPM_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)\b", re.IGNORECASE)

NAME_COMMA_RE = re.compile(r"^\s*([^,]+)\s*,\s*(.+?)\s*$")  # "Last, First Middle"
TITLE_LANG_RE = re.compile(r"\((M|C|E)\)")

# Simple detection tokens
NA_RE = re.compile(r"^\s*(?:N/?A|NA|-)\s*$", re.IGNORECASE)


MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

# Special month encoding in tour code (index-5 char)
TOUR_MONTH_CODE = {
    **{str(i): i for i in range(1, 10)},
    "A": 10, "B": 11, "C": 12
}


# ----------------------------
# Utilities
# ----------------------------

def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iso_from_mmddyyyy(mm: str, dd: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"


def iso_from_mmm_d_yyyy(mmm: str, d: str, yyyy: str) -> Optional[str]:
    m = MONTH_MAP.get(mmm.strip().upper())
    if not m:
        return None
    mm = f"{m:02d}"
    dd = f"{int(d):02d}"
    return f"{yyyy}-{mm}-{dd}"


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def safe_lower(s: Optional[str]) -> Optional[str]:
    return s.lower() if s else None


def is_na(s: Optional[str]) -> bool:
    if s is None:
        return True
    return bool(NA_RE.match(s.strip()))


def find_all_text_blobs(obj: Any) -> List[str]:
    """
    Recursively collect all strings from a JSON-like object.
    This lets us handle multiple extract formats without hard-coding keys.
    """
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


def group_text_by_booking(merged_obj: Any) -> Dict[str, str]:
    """
    For merged JSON:
    - Find occurrences of "SIG_CAN XXXXX" or "SUP_CAN XXXXX"
    - Group text near each occurrence into one blob per booking.

    Heuristic:
    - We concatenate all text blobs, then split by booking markers.
    """
    blobs = find_all_text_blobs(merged_obj)
    joined = "\n".join([b for b in blobs if b and len(b) > 0])

    # Find booking markers positions
    matches = list(BK_RE.finditer(joined))
    if not matches:
        # fallback: bkrId
        bkr_matches = list(BKRID_RE.finditer(joined))
        if not bkr_matches:
            return {}
        # if only bkrId exists, still group by nearest bkrId markers
        matches = bkr_matches  # type: ignore

    # Slice between markers
    booking_map: Dict[str, str] = {}
    for i, m in enumerate(matches):
        bk = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(joined)
        chunk = joined[start:end].strip()
        booking_map[bk] = chunk
    return booking_map


# ----------------------------
# Core parse components (heuristic)
# ----------------------------

@dataclass
class ClientIdentity:
    first_name: str
    last_name: str
    dob: str  # ISO
    gender: str  # M/F/Other (from Ms/Mr etc.)

    def lookup_key(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dob": self.dob,
            "gender": self.gender,
        }


def parse_sales_user(text: str) -> Optional[str]:
    # Examples: "Sales : kai.hu" or "Supera Rep: louis.wu"
    m = re.search(r"\b(?:Sales|Supera\s+Rep)\s*[:：]\s*([a-zA-Z0-9_.-]+)\b", text)
    return m.group(1) if m else None


def parse_created_at(text: str) -> Optional[str]:
    # Prefer explicit Created at line
    m = re.search(r"\bCreated\s+at\s*[:：]?\s*(\d{2}/\d{2}/\d{4})\b", text, re.IGNORECASE)
    if m:
        mm, dd, yyyy = m.group(1).split("/")
        return iso_from_mmddyyyy(mm, dd, yyyy)
    # Otherwise first MM/DD/YYYY in doc
    m2 = DATE_MMDDYYYY_RE.search(text)
    if m2:
        return iso_from_mmddyyyy(m2.group(1), m2.group(2), m2.group(3))
    return None


def parse_group_no(text: str) -> Optional[int]:
    m = re.search(r"\bGroup\s*No\.?\s*[:：]?\s*(\d+)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def parse_currency(text: str) -> Optional[str]:
    m = re.search(r"\bCurrency\s*[:：]?\s*([A-Z]{3})\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Often CAD appears near totals
    if "CAD" in text:
        return "CAD"
    return None


def parse_status(text: str) -> Optional[str]:
    # Heuristics based on keywords
    t = text.lower()
    if "cancel" in t or "cxl" in t:
        return "CANCELLED"
    if "draft" in t:
        return "DRAFT"
    if "deposit" in t:
        return "DEPOSIT"
    if "paid" in t:
        return "PAID"
    if "invoiced" in t:
        return "INVOICED"
    return None


def parse_language(text: str) -> Optional[str]:
    # Find "(M)" "(C)" "(E)" near title area or language field
    m = TITLE_LANG_RE.search(text)
    if m:
        return m.group(1)
    m2 = re.search(r"\bTour\s+Language\s*[:：]?\s*(M|C|E)\b", text, re.IGNORECASE)
    if m2:
        return m2.group(1).upper()
    return None


def parse_client_name_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Returns (last, first) from "Last, First Middle".
    """
    m = NAME_COMMA_RE.match(line)
    if not m:
        return None
    last = norm_space(m.group(1))
    first = norm_space(m.group(2))
    return last, first


def parse_clients(text: str) -> List[ClientIdentity]:
    """
    Heuristic: find lines that look like "Last, First ...", then follow with DOB and gender markers.
    Gender:
      - Ms -> F
      - Mr -> M
      - If not available, leave as "U" (unknown) but your rule prefers stable key.
        In practice your extracts usually include Ms/Mr.
    DOB: prefer "DOB: Apr 07 1953" patterns.
    """
    clients: List[ClientIdentity] = []
    lines = [norm_space(x) for x in text.splitlines() if norm_space(x)]
    for i, line in enumerate(lines):
        nm = parse_client_name_line(line)
        if not nm:
            continue

        last, first = nm

        # search next ~8 lines for DOB + title gender
        window = " \n".join(lines[i:i+10])

        # Gender token:
        gender = "U"
        if re.search(r"\bMr\b", window):
            gender = "M"
        elif re.search(r"\bMs\b", window):
            gender = "F"

        # DOB:
        dob_iso = None
        mdob = re.search(r"\bDOB\s*[:：]?\s*([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b", window, re.IGNORECASE)
        if mdob:
            dob_iso = iso_from_mmm_d_yyyy(mdob.group(1), mdob.group(2), mdob.group(3))

        if dob_iso and gender != "U":
            clients.append(ClientIdentity(first_name=first, last_name=last, dob=dob_iso, gender=gender))

    # Dedup by lookup_key
    uniq: Dict[Tuple[str, str, str, str], ClientIdentity] = {}
    for c in clients:
        k = (c.first_name, c.last_name, c.dob, c.gender)
        uniq[k] = c
    return list(uniq.values())


def parse_health_notes(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract:
      - Meals Res -> dietary_restrictions
      - Motion Sickness -> allergies
    Returns dict with keys "dietary_restrictions", "allergies"
    """
    out = {
        "dietary_restrictions": {"incoming": None, "action": "SKIP_EMPTY"},
        "allergies": {"incoming": None, "action": "SKIP_EMPTY"},
    }

    m_meal = re.search(r"\bMeals\s+Res\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_meal:
        v = norm_space(m_meal.group(1))
        if v and not is_na(v):
            out["dietary_restrictions"] = {"incoming": v, "action": "APPEND_IF_NEW"}

    m_motion = re.search(r"\bMotion\s+Sickness\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_motion:
        v = norm_space(m_motion.group(1))
        if v and not is_na(v):
            out["allergies"] = {"incoming": v, "action": "APPEND_IF_NEW"}

    return out


def parse_tour_code(text: str) -> Optional[str]:
    m = re.search(r"\bTour\s+Code\s*[:：]?\s*([A-Z]{3}\d{5}[A-Z0-9]{1,3})\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Fallback: look for pattern like JPN22917CE
    m2 = re.search(r"\b([A-Z]{3}\d{5}[A-Z0-9]{1,3})\b", text)
    return m2.group(1).upper() if m2 else None


def parse_product_from_tour_code(tour_code: str, tour_language: Optional[str]) -> Dict[str, str]:
    """
    Your locked rules:
    - product unique code is index 8 and 9 in tour code (9 may be missing)
    - departure mdd encoding: index 5 for month (1-9 A B C), index 6-7 day
    - unique seq can be impacted when tour_language is E and tour_code endswith E:
        if tour_language == E and tour_code endswith E, treat trailing E as language indicator,
        unique seq should exclude that trailing E.
    """
    # Example: JPN22917CE
    # indexes: 0.. ; assume at least 9 length
    # country = first 3 letters
    country = tour_code[:3]

    # Unique sequence: indices 8,9 (1-based would be 9th,10th chars). In 0-based:
    # index 8 is 9th char; index 9 is 10th char.
    uniq8 = tour_code[8] if len(tour_code) > 8 else " "
    uniq9 = tour_code[9] if len(tour_code) > 9 else " "

    raw_unique = (uniq8 + uniq9).strip()

    # English trailing E rule:
    if tour_language == "E" and tour_code.endswith("E"):
        # If raw_unique ends with E, drop it as language indicator
        if raw_unique.endswith("E") and len(raw_unique) >= 2:
            raw_unique = raw_unique[:-1].strip()

    # If still empty, keep at least uniq8
    if not raw_unique:
        raw_unique = uniq8.strip() or " "

    return {"country_code": country, "unique_seq": raw_unique}


def parse_dates_from_text(text: str) -> Dict[str, Optional[str]]:
    """
    Find start/end dates in MM/DD/YYYY or MMM D YYYY style.
    Very heuristic: pick first two dates that look like tour dates.
    """
    dates: List[str] = []

    for m in DATE_MMDDYYYY_RE.finditer(text):
        dates.append(iso_from_mmddyyyy(m.group(1), m.group(2), m.group(3)))

    for m in DATE_MMM_D_YYYY_RE.finditer(text):
        iso = iso_from_mmm_d_yyyy(m.group(1), m.group(2), m.group(3))
        if iso:
            dates.append(iso)

    # Dedup preserve order
    seen = set()
    ordered: List[str] = []
    for d in dates:
        if d not in seen:
            seen.add(d)
            ordered.append(d)

    # Heuristic: earliest as start, next as end
    if len(ordered) >= 2:
        return {"start_date": ordered[0], "end_date": ordered[1]}
    if len(ordered) == 1:
        return {"start_date": ordered[0], "end_date": None}
    return {"start_date": None, "end_date": None}


def parse_invoice_items(text: str, currency: str) -> List[Dict[str, Any]]:
    """
    Your locked rule: invoice item totals are auto-calculated from qty*unit_price.
    We output only (quantity, unit_price, currency), plus category/description if we can.
    Coupon/discount:
      - only create coupon items if concession total > 0 (handled outside by checking concession total)
      - coupon items are invoice-level (NOT tied to customer), qty=1, unit_price negative
    """
    items: List[Dict[str, Any]] = []

    # Heuristic: find "CAD 5,150" style passenger prices; count occurrences
    price_matches = re.findall(r"\bCAD\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\b", text, re.IGNORECASE)
    # This will also pick totals; we need passenger lines; use a narrower heuristic:
    passenger_lines = []
    for line in text.splitlines():
        if re.search(r"\bCAD\s*[0-9]", line, re.IGNORECASE) and ("Total" not in line) and ("Balance" not in line):
            passenger_lines.append(line)

    for line in passenger_lines:
        m = re.search(r"\bCAD\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\b", line, re.IGNORECASE)
        if not m:
            continue
        unit = int(m.group(1).replace(",", ""))
        # many extracts list "x 2" or "×2" for count
        qty = 1
        mq = re.search(r"(?:x|×)\s*(\d+)\b", line, re.IGNORECASE)
        if mq:
            qty = int(mq.group(1))
        # If qty>1 we produce multiple rows or one aggregated row?
        # Your examples treat each passenger as qty=1 rows.
        if qty <= 1:
            items.append({
                "fields": {"quantity": 1, "unit_price": unit, "currency": currency},
                "meta": {"source_line": norm_space(line), "category": "package"}
            })
        else:
            # expand into multiple passenger items
            for _ in range(qty):
                items.append({
                    "fields": {"quantity": 1, "unit_price": unit, "currency": currency},
                    "meta": {"source_line": norm_space(line), "category": "package", "expanded_from_qty": qty}
                })

    # If nothing found, leave empty; better than guessing.
    return items


def parse_concession_total(text: str) -> int:
    """
    Look for concession totals like:
      Total -CAD260
    Return absolute total discount (positive integer) or 0 if none.
    """
    m = re.search(r"\bTotal\s*[-–—]?\s*CAD\s*([0-9,]+)\b", text, re.IGNORECASE)
    if not m:
        # sometimes "Total -CAD260" or "-CAD 260"
        m2 = re.search(r"\bTotal\s*[-–—]?\s*-?\s*CAD\s*([0-9,]+)\b", text, re.IGNORECASE)
        if not m2:
            return 0
        return int(m2.group(1).replace(",", ""))
    return int(m.group(1).replace(",", ""))


def parse_pdf_totals(text: str) -> Dict[str, Optional[int]]:
    """
    Extract PDF grand total / total paid / balance for integrity checks only.
    """
    def grab(label: str) -> Optional[int]:
        m = re.search(rf"\b{label}\b\s*[:：]?\s*CAD\s*([0-9,]+)\b", text, re.IGNORECASE)
        if not m:
            return None
        return int(m.group(1).replace(",", ""))

    return {
        "grand_total": grab("Grand Total") or grab("Total"),
        "total_paid": grab("Total Paid"),
        "balance": grab("Balance")
    }


def compute_integrity(items: List[Dict[str, Any]], payments: List[Dict[str, Any]], pdf_totals: Dict[str, Optional[int]]) -> Dict[str, Any]:
    items_sum = 0
    for it in items:
        f = it.get("fields", {})
        q = int(f.get("quantity", 0) or 0)
        u = int(f.get("unit_price", 0) or 0)
        items_sum += q * u

    payments_sum = 0
    for p in payments:
        amt = p.get("fields", {}).get("amount")
        if isinstance(amt, (int, float)):
            payments_sum += int(amt)

    computed_balance = items_sum - payments_sum

    checks = []
    if pdf_totals.get("grand_total") is not None:
        checks.append({"name": "items_sum_equals_pdf_grand_total", "ok": items_sum == pdf_totals["grand_total"]})
    if pdf_totals.get("total_paid") is not None:
        checks.append({"name": "payments_sum_equals_pdf_total_paid", "ok": payments_sum == pdf_totals["total_paid"]})
    if pdf_totals.get("balance") is not None:
        checks.append({"name": "computed_balance_equals_pdf_balance", "ok": computed_balance == pdf_totals["balance"]})

    return {
        "pdf_totals": pdf_totals,
        "computed": {
            "items_sum": items_sum,
            "payments_sum": payments_sum,
            "computed_balance": computed_balance
        },
        "checks": checks
    }


def address_parse(raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Very light parser. If unreliable, return None + raw for notification.
    Expected: '8080 Park Road Richmond, B.c. V6y 1t1'
    """
    if not raw or is_na(raw):
        return None, None

    r = norm_space(raw)
    # attempt: leading number + street name + city + province + postal
    m = re.search(r"^(\d+)\s+(.+?)\s+([A-Za-z.\s]+)\s+([A-Za-z]{2})\.?\s+([A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d)$", r, re.IGNORECASE)
    if not m:
        return None, r

    street_number = m.group(1)
    street_name = norm_space(m.group(2))
    city = norm_space(m.group(3)).rstrip(",")
    prov = m.group(4).upper()
    postal = m.group(5).upper().replace(" ", "")
    postal = f"{postal[:3]} {postal[3:]}" if len(postal) == 6 else postal

    addr = {
        "lookup_key": {
            "street_number": street_number,
            "street_name": street_name,
            "unit_number": None,
            "floor": None,
            "city": city,
            "province": prov,
            "postal_code": postal,
            "country": "Canada"
        },
        "fields": {
            "street_number": street_number,
            "street_name": street_name,
            "unit_number": None,
            "floor": None,
            "city": city,
            "province": prov,
            "postal_code": postal,
            "country": "Canada"
        }
    }
    return addr, None


# ----------------------------
# Main normalization per booking
# ----------------------------

def normalize_booking_text(bk: str, text: str) -> Dict[str, Any]:
    notifications: List[Dict[str, Any]] = []

    created_at = parse_created_at(text)
    group_no = parse_group_no(text)
    currency = parse_currency(text) or "CAD"

    sales_user = parse_sales_user(text) or "__UNKNOWN__"
    status = parse_status(text) or "UNKNOWN"
    tour_language = parse_language(text)

    # Tag rule (simplified): cancelled => record_only; otherwise verified
    tag = "RECORD_ONLY" if status == "CANCELLED" else "VERIFIED"

    tour_code = parse_tour_code(text)
    dates = parse_dates_from_text(text)

    product_bits = {"country_code": None, "unique_seq": None}
    if tour_code:
        product_bits = parse_product_from_tour_code(tour_code, tour_language)

    # Clients
    clients = parse_clients(text)
    health_plan = parse_health_notes(text)

    # Agency & address (if present)
    agency_name = None
    m_agency = re.search(r"\bAgency\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_agency:
        agency_name = norm_space(m_agency.group(1))

    agency_block = None
    address_block = None
    agent_plan = None

    if agency_name and not is_na(agency_name):
        # Try to extract address string line (very heuristic)
        m_addr = re.search(r"\bAddress\s*[:：]?\s*(.+)", text, re.IGNORECASE)
        raw_addr = norm_space(m_addr.group(1)) if m_addr else None

        address_block, addr_raw_fallback = address_parse(raw_addr or "")
        if addr_raw_fallback:
            notifications.append({
                "severity": "INFO",
                "booking_number": bk,
                "field": "agency.address",
                "message": f"Could not parse address into structured fields. Raw: {addr_raw_fallback}"
            })

        agency_fields = {
            "name": agency_name,
            "phone": None,
            "email": None,
            "business_number": None,
            "address_lookup_key": address_block["lookup_key"] if address_block else None
        }
        agency_block = {"lookup_key": {"name": agency_name}, "fields": agency_fields}

        # NEW LOCKED RULE: if agency present but agent missing/NA -> create placeholder agent under agency
        # Detect "Agent: N/A" or missing agent fields (heuristic: search for "Agent:" line)
        m_agent = re.search(r"\bAgent\s*[:：]?\s*(.+)", text, re.IGNORECASE)
        agent_raw = norm_space(m_agent.group(1)) if m_agent else None

        if (agent_raw is None) or is_na(agent_raw):
            agent_plan = {
                "action": "LOOKUP_OR_CREATE_PLACEHOLDER",
                "agent": {
                    "lookup_key": {
                        "agency_lookup_key": {"name": agency_name},
                        "placeholder_code": "UNKNOWN"
                    },
                    "fields": {
                        "first_name": "Unknown",
                        "last_name": "Agent",
                        "department": None,
                        "agency_lookup_key": {"name": agency_name},
                        "notes_append": [
                            "Auto-created placeholder for imports where agency exists but agent is missing/NA"
                        ]
                    }
                }
            }
            notifications.append({
                "severity": "INFO",
                "booking_number": bk,
                "field": "invoice.agent",
                "message": f"Agency {agency_name} present but agent missing/NA. Placeholder agent UNKNOWN assigned."
            })

    # Invoice notes (header coupon notes, airport record-only, logs)
    invoice_notes: List[Dict[str, Any]] = []

    # Coupon header notes: include as invoice note (not item) unless concession total indicates coupon items
    m_coupon_note = re.search(r"\bCAD\s*\d+\s*\(.+?\)\s*off\b.+", text, re.IGNORECASE)
    if m_coupon_note:
        invoice_notes.append({
            "fields": {
                "created_at": created_at,
                "author_user_username": sales_user,
                "description": norm_space(m_coupon_note.group(0))
            }
        })

    # Airports: record-only in invoice notes; do not store on tour_instance
    m_air = re.search(r"\b([A-Z]{3})\s*[-–—>]+\s*([A-Z]{3})\b", text)
    if m_air:
        invoice_notes.append({
            "fields": {
                "created_at": created_at,
                "author_user_username": sales_user,
                "description": f"[Airports] {m_air.group(1)} -> {m_air.group(2)} (not stored on TourInstance; record-only)"
            }
        })

    # Invoice items
    items = parse_invoice_items(text, currency)

    # Concession handling:
    # If concession total > 0 => create coupon items as negative unit_price, invoice-level (not tied to customer)
    # Else no coupon items.
    concession_total = parse_concession_total(text)
    if concession_total > 0:
        # try to find each coupon row amount, else fallback split evenly? (best effort)
        row_amts = []
        for m in re.finditer(r"\bCoupon\b.*?\bCAD\s*([0-9,]+)\b", text, re.IGNORECASE):
            row_amts.append(int(m.group(1).replace(",", "")))
        if not row_amts:
            row_amts = [concession_total]  # single row
        for idx, amt in enumerate(row_amts, start=1):
            items.append({
                "fields": {
                    "quantity": 1,
                    "unit_price": -amt,
                    "currency": currency
                },
                "meta": {"category": "coupon", "source_ref": f"ConcessionRow#{idx}"}
            })

    # Travel documents: only create if doc number not N/A
    travel_documents = []
    for c in clients:
        # Heuristic parse doc number near name
        # (Your actual per-form JSON contains this more reliably; this fallback is text-only)
        # We'll emit an empty list if can't find.
        pass

    # Preferred language merge rule notes:
    # We only *output* preferred_language when present; importer handles:
    # - if incoming is null -> don't update existing
    # - if incoming differs from DB -> notify user
    # Here, we include preferred_language in client fields if found in the text.
    client_blocks = []
    for c in clients:
        client_blocks.append({
            "lookup_key": c.lookup_key(),
            "fields": {
                "first_name": c.first_name,
                "last_name": c.last_name,
                "dob": c.dob,
                "gender": c.gender,
                "preferred_language": tour_language  # best effort; if not truly present, set None below
            },
            "client_health_update_plan": health_plan
        })

    # If we didn't truly detect tour_language, keep preferred_language null
    if tour_language is None:
        for cb in client_blocks:
            cb["fields"]["preferred_language"] = None

    # Tour instance & product
    product_block = None
    tour_instance_block = None
    if tour_code:
        # NOTE: no airport fields here
        product_block = {
            "lookup_key": {
                "country_code": product_bits["country_code"],
                "unique_seq": product_bits["unique_seq"],
                "name": None  # name needs form field; leave None if not parseable from text
            },
            "fields": {
                "country_code": product_bits["country_code"],
                "unique_seq": product_bits["unique_seq"],
                "name": None
            }
        }
        tour_instance_block = {
            "lookup_key": {"tour_code": tour_code, "tour_language": tour_language},
            "fields": {
                "tour_code": tour_code,
                "tour_language": tour_language,
                "start_date": dates.get("start_date"),
                "end_date": dates.get("end_date"),
                "product_lookup_key": product_block["lookup_key"] if product_block else None
            }
        }

    # Payments: for now create empty; your per-form extracts have the tables; implement there.
    payments: List[Dict[str, Any]] = []

    # Integrity totals from PDF
    pdf_totals = parse_pdf_totals(text)
    integrity = compute_integrity(items, payments, pdf_totals)

    # If integrity fails, notify
    for chk in integrity.get("checks", []):
        if chk.get("ok") is False:
            notifications.append({
                "severity": "WARN",
                "booking_number": bk,
                "field": "integrity",
                "message": f"Integrity check failed: {chk['name']}"
            })

    # Build output
    out: Dict[str, Any] = {
        "meta": {
            "booking_number": bk,
            "created_at": created_at,
            "group_no": group_no,
            "source": {"type": "merged_text_block", "marker": f"SIG_CAN/SUP_CAN {bk}"}
        },
        "invoice": {
            "lookup_key": {"booking_number": bk},
            "fields": {
                "status": status,
                "tag": tag,
                "currency": currency,
                "group_no": group_no,
                "created_at": created_at,
                "sales_user_username": sales_user,
                **({"agent_lookup_key": agent_plan["agent"]["lookup_key"]} if agent_plan else {})
            }
        },
        "sales_user": {"lookup_key": {"username": sales_user}},
        "agent_plan": agent_plan,
        "address": address_block,
        "agency": agency_block,
        "product": product_block,
        "tour_instance": tour_instance_block,
        "clients": client_blocks,
        "travel_documents": travel_documents,
        "invoice_items": items,
        "invoice_notes": invoice_notes,
        "payments": payments,
        "integrity": integrity,
        "discrepancy_policy": {
            "mode": "APPEND_NOTIFY_NO_OVERWRITE",
            "notifications": notifications
        }
    }
    return out


# ----------------------------
# Entry points
# ----------------------------

def extract_booking_texts_from_file(path: str | Path) -> Dict[str, str]:
    obj = load_json(path)
    # If it's a single-booking extract, it may not contain SIG_CAN marker.
    # We'll try to infer booking number from filename.
    booking_map = group_text_by_booking(obj)

    if booking_map:
        return booking_map

    # Single booking fallback: use whole doc as one blob, bk from filename
    bk_guess = re.findall(r"\d{5,6}", Path(path).stem)
    bk = bk_guess[0] if bk_guess else "UNKNOWN"
    blobs = find_all_text_blobs(obj)
    joined = "\n".join([b for b in blobs if b])
    return {bk: joined}


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", help="Path to merged JSON or single booking JSON")
    ap.add_argument("--out", default="normalized_out.json", help="Output file path")
    ap.add_argument("--only", default=None, help="Only process this booking number, e.g. 344565")
    args = ap.parse_args()

    booking_texts = extract_booking_texts_from_file(args.input_json)
    if not booking_texts:
        raise SystemExit("No bookings found (no SIG_CAN/SUP_CAN markers and could not infer).")

    bks = sorted(booking_texts.keys(), key=lambda x: int(x) if x.isdigit() else 9999999)

    if args.only:
        bks = [bk for bk in bks if bk == args.only]

    normalized = {}
    for bk in bks:
        normalized[bk] = normalize_booking_text(bk, booking_texts[bk])

    Path(args.out).write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(normalized)} normalized booking(s) to {args.out}")
    print("Booking numbers:", ", ".join(sorted(normalized.keys(), key=lambda x: int(x) if x.isdigit() else 9999999)))


if __name__ == "__main__":
    main()