from typing import Dict, Any

from .header_parser import (
    parse_created_at, parse_group_no, parse_currency, parse_sales_user,
    parse_status, parse_language, parse_tour_code, parse_dates_from_text,
    parse_product_from_tour_code, parse_product_name
)
from .client_parser import parse_clients, parse_health_notes
from .agency_parser import parse_agency_and_agent
from .flight_parser import parse_flights
from .financial_parser import parse_invoice_items, handle_concessions, parse_pdf_totals, parse_payments
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
    product_name = parse_product_name(text, tour_code)

    product_bits = parse_product_from_tour_code(tour_code, tour_language) if tour_code else {}

    clients = parse_clients(text)
    health_plan = parse_health_notes(text)

    agency_block, address_block, agent_plan = parse_agency_and_agent(text, bk, notifications)

    client_blocks = []
    all_client_tickets = []
    tour_bookings = []
    
    airlines, airports, flights, flight_instances, tickets_by_pnr = parse_flights(text)
    import uuid
    pnr_keys = list(tickets_by_pnr.keys())
    ticket_templates = tickets_by_pnr[pnr_keys[0]] if pnr_keys else []
    
    for i, c in enumerate(clients):
        tb_lookup = {"booking_id": f"{bk}-TB-{i+1}"}
        tour_bookings.append({
            "lookup_key": tb_lookup,
            "fields": {
                "booking_id": f"{bk}-TB-{i+1}",
                "booking_type": "",
                "room_type": getattr(c, 'room_type', ''),
                "tour_instance_lookup": {
                    "tour_code": tour_code,
                    "tour_language": tour_language
                }
            }
        })
        
        c_fields = {
            "first_name": c.first_name, "last_name": c.last_name,
            "dob": c.dob, "gender": c.gender,
            "preferred_language": tour_language
        }
        if getattr(c, 'phone', None): c_fields["phone"] = c.phone
        if getattr(c, 'email', None): c_fields["email"] = c.email

        travel_docs = []
        if getattr(c, 'passport', None):
            travel_docs.append(c.passport)

        client_tickets = []
        for t in ticket_templates:
            hexcode = uuid.uuid4().hex[:6]
            fcode = t["flight_instance_lookup"]["flight_code"]
            t_obj = {
                "ticket_code": f"{fcode}-ANY-{hexcode}",
                "pnr": t["pnr"],
                "meal_plan": t["meal_plan"],
                "flight_instance_lookup": t["flight_instance_lookup"]
            }
            client_tickets.append(t_obj)
            all_client_tickets.append(t_obj)

        client_blocks.append({
            "lookup_key": c.lookup_key(),
            "fields": c_fields,
            "health_plan": health_plan,
            "travel_documents": travel_docs,
            "flight_tickets": client_tickets,
            "tour_booking_lookup": tb_lookup
        })

    invoice_notes = []

    items = parse_invoice_items(text, currency, client_blocks, all_client_tickets)
    items = handle_concessions(text, items, currency)
    payments = parse_payments(text, currency)

    product_block = None
    tour_instance_block = None
    if tour_code:
        product_block = {
            "lookup_key": {"country_code": product_bits.get("country_code"), "unique_seq": product_bits.get("unique_seq")},
            "fields": {
                "country_code": product_bits.get("country_code"),
                "unique_seq": product_bits.get("unique_seq"),
                "name": product_name
            }
        }
        tour_instance_block = {
            "lookup_key": {"tour_code": tour_code, "tour_language": tour_language},
            "fields": {
                "tour_code": tour_code, "tour_language": tour_language,
                "start_date": dates.get("start_date"), "end_date": dates.get("end_date"),
                "product_lookup_key": product_block["lookup_key"]
            }
        }


    pdf_totals = parse_pdf_totals(text)
    integrity = compute_integrity(items, payments, pdf_totals)

    for chk in integrity.get("checks", []):
        if not chk.get("ok"):
            notifications.append({"severity": "WARN", "booking_number": bk, "message": f"Integrity failed: {chk['name']}"})

    return {
        "airports": airports,
        "airlines": airlines,
        "flights": flights,
        "flight_instances": flight_instances,
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
        "tour_bookings": tour_bookings,
        "agency": agency_block,
        "agent_plan": agent_plan,
        "address": address_block,
        "invoice_items": items,
        "payments": payments,
        "integrity": integrity,
        "notifications": notifications
    }
