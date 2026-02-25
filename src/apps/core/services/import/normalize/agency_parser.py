import re
from typing import Dict, Any, Tuple, Optional, List
from .utils import norm_space, is_na

def address_parse(raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not raw or is_na(raw):
        return None, None
    r = norm_space(raw)
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
            "street_number": street_number, "street_name": street_name, "unit_number": None,
            "floor": None, "city": city, "province": prov, "postal_code": postal, "country": "Canada"
        },
        "fields": {
            "street_number": street_number, "street_name": street_name, "unit_number": None,
            "floor": None, "city": city, "province": prov, "postal_code": postal, "country": "Canada"
        }
    }
    return addr, None

def parse_agency_and_agent(text: str, bk: str, notifications: List[Dict[str, Any]]) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    agency_name = None
    m_agency = re.search(r"\bAgency\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_agency:
        agency_name = norm_space(m_agency.group(1))

    if not agency_name or is_na(agency_name):
        return None, None, None

    m_addr = re.search(r"\bAddress\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    raw_addr = norm_space(m_addr.group(1)) if m_addr else None
    address_block, addr_raw_fallback = address_parse(raw_addr or "")

    if addr_raw_fallback:
        notifications.append({
            "severity": "INFO", "booking_number": bk, "field": "agency.address",
            "message": f"Could not parse address. Raw: {addr_raw_fallback}"
        })

    agency_block = {
        "lookup_key": {"name": agency_name},
        "fields": {
            "name": agency_name, "phone": None, "email": None, "business_number": None,
            "address_lookup_key": address_block["lookup_key"] if address_block else None
        }
    }

    agent_plan = None
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
                    "first_name": "Unknown", "last_name": "Agent", "department": None,
                    "agency_lookup_key": {"name": agency_name},
                    "notes_append": ["Auto-created placeholder for missing/NA agent"]
                }
            }
        }
        notifications.append({
            "severity": "INFO", "booking_number": bk, "field": "invoice.agent",
            "message": f"Agency {agency_name} present but agent missing. Placeholder assigned."
        })

    return agency_block, address_block, agent_plan
