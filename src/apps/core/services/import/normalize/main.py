from typing import Dict, Any

from .header_parser import (
    parse_created_at, parse_group_no, parse_currency, parse_sales_user,
    parse_status, parse_language, parse_tour_code, parse_dates_from_text,
    parse_product_from_tour_code
)
from .client_parser import parse_clients, parse_health_notes
from .financial_parser import parse_invoice_items, handle_concessions, parse_pdf_totals
from .agency_parser import parse_agency_and_agent
from .integrity import compute_integrity

def normalize_booking_text(bk: str, text: str) -> Dict[str, Any]:
    notifications = []
    created_at = parse_created_at(text)
    group_no = parse_group_no(text)
    currency = parse_currency(text) or "CAD"
    sales_user = parse_sales_user(text) or "__UNKNOWN__"
    status = parse_status(text) or "UNKNOWN"
    tour_language = parse_language(text)
    tag = "RECORD_ONLY" if status == "CANCELLED" else "VERIFIED"
    tour_code = parse_tour_code(text)
    dates = parse_dates_from_text(text)

    product_bits = parse_product_from_tour_code(tour_code, tour_language) if tour_code else {}

    clients = parse_clients(text)
    health_plan = parse_health_notes(text)

    agency_block, address_block, agent_plan = parse_agency_and_agent(text, bk, notifications)

    invoice_notes = []
    # Simplified Note logic (no regex needed here as it was in original, just adding placeholder)

    items = parse_invoice_items(text, currency)
    items = handle_concessions(text, items, currency)

    client_blocks = []
    for c in clients:
        client_blocks.append({
            "lookup_key": c.lookup_key(),
            "fields": {
                "first_name": c.first_name, "last_name": c.last_name,
                "dob": c.dob, "gender": c.gender,
                "preferred_language": tour_language
            },
            "health_plan": health_plan
        })

    product_block = None
    tour_instance_block = None
    if tour_code:
        product_block = {
            "lookup_key": {"country_code": product_bits.get("country_code"), "unique_seq": product_bits.get("unique_seq")},
            "fields": {"country_code": product_bits.get("country_code"), "unique_seq": product_bits.get("unique_seq")}
        }
        tour_instance_block = {
            "lookup_key": {"tour_code": tour_code, "tour_language": tour_language},
            "fields": {
                "tour_code": tour_code, "tour_language": tour_language,
                "start_date": dates.get("start_date"), "end_date": dates.get("end_date"),
                "product_lookup_key": product_block["lookup_key"]
            }
        }

    payments = [] # Implement logic later per form extract
    pdf_totals = parse_pdf_totals(text)
    integrity = compute_integrity(items, payments, pdf_totals)

    for chk in integrity.get("checks", []):
        if not chk.get("ok"):
            notifications.append({"severity": "WARN", "booking_number": bk, "message": f"Integrity failed: {chk['name']}"})

    return {
        "invoice": {
            "lookup_key": {"booking_number": bk},
            "fields": {
                "status": status, "tag": tag, "currency": currency, "group_no": group_no,
                "created_at": created_at, "sales_user_username": sales_user,
                **({"agent_lookup_key": agent_plan["agent"]["lookup_key"]} if agent_plan else {})
            }
        },
        "clients": client_blocks,
        "product": product_block,
        "tour_instance": tour_instance_block,
        "agency": agency_block,
        "agent_plan": agent_plan,
        "address": address_block,
        "invoice_items": items,
        "integrity": integrity,
        "notifications": notifications
    }
