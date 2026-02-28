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
            "meta": {"category": "flight_ticket", "client_lookup": ft.get("client_lookup")}
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
            # User Feedback: Retain all cancelled entries with full amounts intact
            # Removed the CXD/CXL lookahead abortion flag logic.
            
            for j in range(1, 15):
                if i + j >= len(lines): break
                nxt = lines[i+j]
                if (nxt.startswith("CAD") or nxt.startswith(currency)) and amt is None:
                    m = re.search(r"([0-9,]+)", nxt)
                    if m: amt = int(m.group(1).replace(",", ""))
                elif nxt.isdigit() and amt is not None and not remark:
                    pass # skip quantity line
                elif nxt in ["System", "Discount", "Total:", "Total"] and amt is not None:
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
        if lines[i] == "Deposit" or lines[i] == "Payment":
            amt = None
            remark = ""
            # User Feedback: Retain all cancelled payment entries
            # Removed the CXD/CXL lookahead abortion flag logic.
            
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
                elif nxt in ["Louis", "Esther", "System", "Payment", "Balance", "Deposit"] and amt is not None:
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

def parse_logs(text: str) -> List[Dict[str, Any]]:
    notes = []
    lines = [L.strip() for L in text.splitlines() if L.strip()]
    
    # Isolate just the Logs portion, often appearing near the end of the PDF
    try:
        start_idx = lines.index("Logs")
    except ValueError:
        return notes
        
    log_lines = lines[start_idx:]
    
    for i in range(len(log_lines)):
        # We look for the standard Timestamp printed sequentially in the history block
        # Format: MM/DD/YYYY H:MM(AM/PM)
        m_date = re.search(r"^(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}[AP]M)$", log_lines[i], re.IGNORECASE)
        if m_date:
            date_str = m_date.group(1)
            time_str = m_date.group(2)
            # Reformat to ISO for DB (just MM/DD/YYYY is enough for basic ISO creation, or we can use utils)
            from .utils import iso_from_mmddyyyy
            mm, dd, yyyy = date_str.split("/")
            iso_date = iso_from_mmddyyyy(mm, dd, yyyy)
            
            # The Type is almost always the line AFTER the Date
            log_type = "Note"
            if i + 1 < len(log_lines):
                log_type = log_lines[i+1]
                
            # The Description is almost always the line AFTER the Type
            description = ""
            if i + 2 < len(log_lines):
                description = log_lines[i+2]
                
            # The Author is the line AFTER the Description
            author = "system"
            if i + 3 < len(log_lines):
                author = log_lines[i+3]
                
            # Construct standard InvoiceNote shape
            # Provide full 'fields' for the author so update_or_create can safely make empty users
            notes.append({
                "fields": {
                    "content": f"[{log_type}] {description}",
                    "created_at": iso_date
                },
                "author": {
                    "lookup_key": {
                        "username": author.lower()
                    },
                    "fields": {
                        "username": author.lower(),
                        "is_active": False  # safely default generated historical agents
                    }
                }
            })
            
    return notes
