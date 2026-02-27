import re
from typing import Dict, Any, List, Optional
from .utils import norm_space

def parse_invoice_items(text: str, currency: str, clients: list, flight_tickets: list) -> List[Dict[str, Any]]:
    base_price = 5150
    for line in text.splitlines():
        # Specifically target the Adult Fare line (e.g. "A CAD5,150")
        m = re.search(r"\bA\s+CAD\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\b", line, re.IGNORECASE)
        if m:
            base_price = int(m.group(1).replace(",", ""))
            break

    items: List[Dict[str, Any]] = []
    
    for c in clients:
        items.append({
            "fields": {"quantity": 1, "unit_price": base_price, "currency": currency},
            "tour_booking_lookup": c.get("tour_booking_lookup"),
            "meta": {"category": "tour_booking", "client_lookup": c["lookup_key"]}
        })

    for ft in flight_tickets:
        items.append({
            "fields": {"quantity": 1, "unit_price": 0, "currency": currency},
            "flight_ticket_lookup": {"ticket_code": ft["ticket_code"]},
            "meta": {"category": "flight_ticket"}
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
    lines = [L.strip() for L in text.splitlines() if L.strip()]
    
    for i in range(len(lines)):
        if lines[i] == "Discount":
            amt = None
            remark = ""
            for j in range(1, 15):
                if i + j >= len(lines): break
                nxt = lines[i+j]
                if (nxt.startswith("CAD") or nxt.startswith(currency)) and amt is None:
                    m = re.search(r"([0-9,]+)", nxt)
                    if m: amt = int(m.group(1).replace(",", ""))
                elif nxt.isdigit() and amt is not None and not remark:
                    pass # skip quantity line
                elif nxt in ["System", "CXD", "Discount", "Total:", "Total"]:
                    break
                elif amt is not None:
                    remark += nxt + " "

            if amt is not None:
                items.append({
                    "fields": {
                        "quantity": 1,
                        "unit_price": -amt,
                        "currency": currency
                    },
                    "meta": {"category": "discount", "remark": remark.strip() or "Discount"}
                })
    return items

def parse_payments(text: str, currency: str) -> List[Dict[str, Any]]:
    payments = []
    lines = [L.strip() for L in text.splitlines() if L.strip()]

    for i in range(len(lines)):
        if lines[i] == "Deposit":
            amt = None
            remark = ""
            for j in range(1, 15):
                if i + j >= len(lines): break
                nxt = lines[i+j]
                if (nxt.startswith("CAD") or nxt.startswith(currency)) and amt is None:
                    m = re.search(r"([0-9,]+)", nxt)
                    if m: amt = int(m.group(1).replace(",", ""))
                elif nxt in ["CK", "CC", "CASH"]:
                    pass # skip FOP
                elif nxt.isdigit() and amt is not None and not remark:
                    pass # skip count
                elif nxt in ["Louis", "Esther", "System", "CXD", "Payment", "Balance"]:
                    break
                elif amt is not None:
                    remark += nxt + " "

            if amt is not None:
                payments.append({
                    "fields": {
                        "amount": amt,
                        "type": "deposit",
                        "currency": currency
                    },
                    "meta": {"remark": remark.strip() or "Deposit"}
                })
    return payments
