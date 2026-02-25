import re
from typing import Dict, Any, List, Optional, Tuple
from .utils import norm_space, iso_from_mmm_d_yyyy, is_na, NAME_COMMA_RE

class ClientIdentity:
    def __init__(self, first_name: str, last_name: str, dob: str, gender: str):
        self.first_name = first_name
        self.last_name = last_name
        self.dob = dob
        self.gender = gender

    def lookup_key(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dob": self.dob,
            "gender": self.gender,
        }

def parse_client_name_line(line: str) -> Optional[Tuple[str, str]]:
    m = NAME_COMMA_RE.match(line)
    if not m:
        return None
    return norm_space(m.group(1)), norm_space(m.group(2))

def parse_clients(text: str) -> List[ClientIdentity]:
    clients: List[ClientIdentity] = []
    lines = [norm_space(x) for x in text.splitlines() if norm_space(x)]

    for i, line in enumerate(lines):
        nm = parse_client_name_line(line)
        if not nm:
            continue

        last, first = nm
        window = " \n".join(lines[i:i+10])

        gender = "U"
        if re.search(r"\bMr\b", window):
            gender = "M"
        elif re.search(r"\bMs\b", window):
            gender = "F"

        dob_iso = None
        mdob = re.search(r"\bDOB\s*[:：]?\s*([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b", window, re.IGNORECASE)
        if mdob:
            dob_iso = iso_from_mmm_d_yyyy(mdob.group(1), mdob.group(2), mdob.group(3))

        if dob_iso and gender != "U":
            clients.append(ClientIdentity(first_name=first, last_name=last, dob=dob_iso, gender=gender))

    # Dedup by lookup_key
    uniq = {}
    for c in clients:
        k = (c.first_name, c.last_name, c.dob, c.gender)
        uniq[k] = c
    return list(uniq.values())

def parse_health_notes(text: str) -> Dict[str, Dict[str, Any]]:
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
