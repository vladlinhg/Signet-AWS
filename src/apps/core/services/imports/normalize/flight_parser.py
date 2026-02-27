import re
import uuid
from typing import List, Dict, Any, Tuple
from .utils import norm_space

def generate_hex(length=6):
    return uuid.uuid4().hex[:length]

def parse_flights(text: str) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], Dict[str, List[Dict]]]:
    airlines = []
    airports = []
    flights = []
    flight_instances = []
    tickets_by_pnr = {}  # Map PNR -> list of ticket objects

    lines = [norm_space(x) for x in text.splitlines() if norm_space(x)]

    # 1. Extract Global PNR
    # PyMuPDF puts the PNR block at the very bottom of the page usually
    global_pnr = "UNKNOWN"
    m_pnr = re.search(r"\bPNR\s*\d*\s*:\s*([A-Z0-9]{5,8})\b", text, re.IGNORECASE)
    if m_pnr:
        global_pnr = m_pnr.group(1).upper()

    tickets_by_pnr[global_pnr] = []

    # 2. Extract Flight Segments (Vertically stacked by PyMuPDF)
    # 60 AC0003
    # 61 09/14/2022
    # 62 YVR/NRT
    # 63 1:15PM - 3:10PM+1

    # We will also extract the Arrangement Notes from the lines following the flight blocks.
    # PyMuPDF puts all notes at the end of the block:
    # 69 Self-arranged (Meet in hotel)
    # 70 Supera arranged
    arrangements = []
    for l in lines:
        if "arranged" in l.lower() or "meet in" in l.lower() or "supera" in l.lower():
            if "hotel ext" not in l.lower() and "rep." not in l.lower():
                arrangements.append(l)

    flight_segments = []
    for i in range(len(lines) - 2):
        # Look for the Airline+Flight Number (e.g. AC0003 or OZ0111)
        m_flight = re.search(r"^([A-Z]+)(\d+)$", lines[i])
        if m_flight:
            # Check if next line is a Date
            m_date = re.search(r"^(\d{2})/(\d{2})/(\d{4})$", lines[i+1])
            # Check if line after is Route (YVR/NRT)
            m_route = re.search(r"^([A-Z]{3})/([A-Z]{3})$", lines[i+2])

            if m_date and m_route:
                flight_segments.append({
                    "airline": m_flight.group(1).upper(),
                    "number": m_flight.group(2),
                    "dep_raw": lines[i+1],
                    "dep_apt": m_route.group(1).upper(),
                    "arr_apt": m_route.group(2).upper()
                })

    # 3. Assemble the DB Objects
    for idx, seg in enumerate(flight_segments):
        airline_code = seg["airline"]
        flight_num = seg["number"]
        dep_apt = seg["dep_apt"]
        arr_apt = seg["arr_apt"]

        # Format Date (MM/DD/YYYY -> YYYY-MM-DD)
        parts = seg["dep_raw"].split('/')
        dep_date = f"{parts[2]}-{parts[0]}-{parts[1]}"

        arr_note = arrangements[idx] if idx < len(arrangements) else ""

        # Build Airline
        airlines.append({"lookup_key": {"code": airline_code}, "fields": {"code": airline_code}})

        # Build Airports
        airports.append({"lookup_key": {"iata_code": dep_apt}, "fields": {"iata_code": dep_apt}})
        airports.append({"lookup_key": {"iata_code": arr_apt}, "fields": {"iata_code": arr_apt}})

        # Build Flight Base
        flights.append({
            "lookup_key": {
                "airline_code": airline_code,
                "flight_number": flight_num,
                "departure_airport_iata": dep_apt,
                "arrival_airport_iata": arr_apt
            },
            "fields": {
                "flight_number": flight_num
            }
        })

        # Build Flight Instance
        flight_code = f"{airline_code}{flight_num}-{dep_apt}-{arr_apt}"
        flight_instances.append({
            "lookup_key": {
                "flight_code": flight_code,
                "departure_date": dep_date
            },
            "fields": {
                "flight_code": flight_code,
                "departure_date": dep_date,
                "flight_lookup": {
                    "airline_code": airline_code,
                    "flight_number": flight_num,
                    "departure_airport_iata": dep_apt,
                    "arrival_airport_iata": arr_apt
                }
            }
        })

        # Build Ticket Stub
        hexcode = generate_hex()
        ticket_code = f"{flight_code}-ANY-{hexcode}"

        tickets_by_pnr[global_pnr].append({
            "pnr": global_pnr,
            "ticket_code": ticket_code,
            "meal_plan": arr_note,
            "flight_instance_lookup": {
                "flight_code": flight_code,
                "departure_date": dep_date
            }
        })

    # Dedup entities globally
    def dedup(lst):
        seen = set()
        out = []
        for x in lst:
            k = str(x['lookup_key'])
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return dedup(airlines), dedup(airports), dedup(flights), dedup(flight_instances), tickets_by_pnr
