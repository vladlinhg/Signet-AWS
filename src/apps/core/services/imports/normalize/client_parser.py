import re
from typing import Dict, Any, List, Optional, Tuple
from .utils import norm_space, iso_from_mmm_d_yyyy, iso_from_mmddyyyy, is_na

class ClientIdentity:
    def __init__(self, first_name: str, last_name: str, dob: str, gender: str, room_type: str = ""):
        self.first_name = first_name
        self.last_name = last_name
        self.dob = dob
        self.gender = gender
        self.room_type = room_type
        self.phone = None
        self.email = None
        self.passport = None

    def lookup_key(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.dob,
            "gender": self.gender,
        }

def parse_clients(text: str) -> List[ClientIdentity]:
    lines = [norm_space(x) for x in text.splitlines() if norm_space(x)]

    # 1. Pull out Global Contact Info block
    global_phone = None
    global_email = None
    m_ph = re.search(r"(\+?\d{1,2}\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", text)
    if m_ph: global_phone = m_ph.group(1).strip()

    m_em = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
    if m_em: global_email = m_em.group(1).strip()

    # 2. Extract Titles & DOBs sequentially
    title_dob_pairs = []
    for i, line in enumerate(lines):
        m_title = re.search(r"^(Mr\.|Mrs\.|Ms\.|Miss|Dr\.)$", line, re.IGNORECASE)
        if m_title:
            title = m_title.group(1)
            gender = "M" if "mr" in title.lower() else "F"

            dob_iso = "1900-01-01" # Sensible fallback if no DOB found
            window = " \n".join(lines[i:i+15])
            mdob = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b", window, re.IGNORECASE)
            if mdob:
                dob_iso = iso_from_mmm_d_yyyy(mdob.group(1), mdob.group(2), mdob.group(3))
            else:
                m2 = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", window)
                if m2:
                    dob_iso = iso_from_mmddyyyy(m2.group(1), m2.group(2), m2.group(3))
                    
            room_type = ""
            if i > 0:
                prev = lines[i-1]
                # If previous line isn't a likely date/email/phone, assume it's the room header
                if not re.search(r"(@|\d{3}-\d{4}|\d{4}-\d{2}-\d{2}|Mr\.|Mrs\.|Ms\.)", prev, re.IGNORECASE):
                    room_type = prev

            title_dob_pairs.append({'gender': gender, 'dob': dob_iso, 'room_type': room_type})

    # 3. Extract Names and Passports sequentially
    names = []
    passports = []
    current_room_type = ""
    for i, line in enumerate(lines):
        # Allow letters, spaces, hyphens and periods in names.
        # Allow first name to be empty if it trails onto the next line
        m_name = re.search(r"^([A-Za-z\s.-]+),\s*([A-Za-z\s.-]*)$", line)
        if m_name:
            last = norm_space(m_name.group(1))
            first = norm_space(m_name.group(2))

            # If first name is completely empty, it might be on the next line (e.g. Ortiz Pedraza)
            if not first and i+1 < len(lines):
                next_part = norm_space(lines[i+1])
                # Ensure the next line is just a name and not a system tag like "PRO" or a date
                if re.match(r"^[A-Za-z\s.-]+$", next_part) and len(next_part) > 1 and next_part.lower() not in ["pro", "total"]:
                    first = next_part

            last_lower = last.lower()
            # Filter out false positives (e.g. system tags)
            if last_lower in ["total", "remark", "discount", "last"]: continue

            # Filter out Contact Info block duplicates like `Mr. Parker, Bryan`
            if last_lower.startswith('mr.') or last_lower.startswith('mrs.') or last_lower.startswith('ms.'): continue

            if last and first:
                if i > 0:
                    prev = lines[i-1]
                    # Filter out purely junk tags or dates
                    if not re.search(r"(CAD|USD|\d{4}|Mr\.|Mrs\.|Ms\.|Total|Discount|Payment|N/A|PRO)", prev, re.IGNORECASE) and len(prev)>1:
                        current_room_type = prev

                names.append({'last': last, 'first': first, 'room_type': current_room_type})

        # Scrape passports nearby (CAN G**4663 | Aug 27 2024)
        m_pass = re.search(r"^([A-Z]{3})\s+([A-Z0-9*]{6,12})$", line, re.IGNORECASE)
        if m_pass:
            country = m_pass.group(1).upper()
            doc_no = m_pass.group(2)

            # Look at the next few lines for an expiry date
            exp_iso = "1900-01-01"
            window = " ".join(lines[i:min(i+5, len(lines))])
            if re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b", window, re.IGNORECASE):
                md = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b", window, re.IGNORECASE)
                exp_iso = iso_from_mmm_d_yyyy(md.group(1), md.group(2), md.group(3))

            passports.append({
                "doc_type": "PASSPORT",
                "doc_number": doc_no,
                "issuing_country": country,
                "expiry_date": exp_iso
            })

    # 4. Zip them together
    clients: List[ClientIdentity] = []
    max_clients = min(len(title_dob_pairs), len(names))

    for i in range(max_clients):
        pair = title_dob_pairs[i]
        name = names[i]
        rt = name.get('room_type', '') or pair.get('room_type', '')
        c = ClientIdentity(first_name=name['first'], last_name=name['last'], dob=pair['dob'], gender=pair['gender'], room_type=rt)
        if i == 0:
            c.phone = global_phone
            c.email = global_email
        if i < len(passports):
            c.passport = passports[i]
        clients.append(c)

    # Dedup by lookup_key
    uniq = {}
    for c in clients:
        k = (c.first_name, c.last_name, c.dob, c.gender)
        if k not in uniq:
            uniq[k] = c

    return list(uniq.values())

def parse_health_notes(text: str) -> Dict[str, Dict[str, Any]]:
    out = {
        "dietary_restrictions": {"incoming": None, "action": "SKIP_EMPTY"},
        "allergies": {"incoming": None, "action": "SKIP_EMPTY"},
    }

    # Strict list of strings to ignore (they are table headers, not values)
    ignore_list = ["motion sickness", "insurance", "remark", "prices", "n/a", "none"]

    m_meal = re.search(r"\bMeals\s+Res\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_meal:
        val = norm_space(m_meal.group(1)).lower()
        if val and val not in ignore_list and not is_na(val):
            out["dietary_restrictions"] = {"incoming": norm_space(m_meal.group(1)), "action": "APPEND_IF_NEW"}

    m_motion = re.search(r"\bMotion\s+Sickness\s*[:：]?\s*(.+)", text, re.IGNORECASE)
    if m_motion:
        val = norm_space(m_motion.group(1)).lower()
        if val and val not in ignore_list and "insurance" not in val and not is_na(val):
            out["allergies"] = {"incoming": norm_space(m_motion.group(1)), "action": "APPEND_IF_NEW"}

    return out
