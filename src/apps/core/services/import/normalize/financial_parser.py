import re
from typing import Dict, Any, List, Optional
from .utils import norm_space

def parse_invoice_items(text: str, currency: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    passenger_lines = []

    for line in text.splitlines():
        if re.search(r"\bCAD\s*[0-9]", line, re.IGNORECASE) and ("Total" not in line) and ("Balance" not in line):
            passenger_lines.append(line)

    for line in passenger_lines:
        m = re.search(r"\bCAD\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\b", line, re.IGNORECASE)
        if not m:
            continue
        unit = int(m.group(1).replace(",", ""))
        qty = 1
        mq = re.search(r"(?:x|×)\s*(\d+)\b", line, re.IGNORECASE)
        if mq:
            qty = int(mq.group(1))

        if qty <= 1:
            items.append({
                "fields": {"quantity": 1, "unit_price": unit, "currency": currency},
                "meta": {"source_line": norm_space(line), "category": "package"}
            })
        else:
            for _ in range(qty):
                items.append({
                    "fields": {"quantity": 1, "unit_price": unit, "currency": currency},
                    "meta": {"source_line": norm_space(line), "category": "package", "expanded_from_qty": qty}
                })
    return items

def parse_concession_total(text: str) -> int:
    m = re.search(r"\bTotal\s*[-–—]?\s*CAD\s*([0-9,]+)\b", text, re.IGNORECASE)
    if not m:
        m2 = re.search(r"\bTotal\s*[-–—]?\s*-?\s*CAD\s*([0-9,]+)\b", text, re.IGNORECASE)
        if not m2:
            return 0
        return int(m2.group(1).replace(",", ""))
    return int(m.group(1).replace(",", ""))

def parse_pdf_totals(text: str) -> Dict[str, Optional[int]]:
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

def handle_concessions(text: str, items: List[Dict[str, Any]], currency: str):
    concession_total = parse_concession_total(text)
    if concession_total > 0:
        row_amts = []
        for m in re.finditer(r"\bCoupon\b.*?\bCAD\s*([0-9,]+)\b", text, re.IGNORECASE):
            row_amts.append(int(m.group(1).replace(",", "")))
        if not row_amts:
            row_amts = [concession_total]
        for idx, amt in enumerate(row_amts, start=1):
            items.append({
                "fields": {
                    "quantity": 1,
                    "unit_price": -amt,
                    "currency": currency
                },
                "meta": {"category": "coupon", "source_ref": f"ConcessionRow#{idx}"}
            })
    return items
