import fitz  # PyMuPDF
import re
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class PDFParserService:
    """
    Parses 'Supernet' style Booking Confirmation PDFs using PyMuPDF.
    Extracts structured data: Header, Passengers, Flights, Financials.
    """

    def __init__(self, file_stream):
        """
        :param file_stream: Binary IO stream of the PDF file.
        """
        self.doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        self.text = ""
        self.full_text_layers = [] # List of text per page

        # Load all text
        for page in self.doc:
            text = page.get_text("text")
            self.full_text_layers.append(text)
            self.text += text + "\n"

    def parse(self):
        """
        Main entry point. Returns a dictionary of extracted data.
        """
        try:
            data = {
                'raw_text_preview': self.text, # Full text for debugging
                'header': self._extract_header(),
                'passengers': self._extract_passengers(),
                'flights': self._extract_flights(),
                'financials': self._extract_financials(),
            }
            return data
        except Exception as e:
            logger.error(f"PDF Parse Error: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    def _extract_header(self):
        """
        Extracts Booking Number, Tour Code, Dates, Agent.
        """
        header_data = {}

        # 1. Booking Number (e.g., "SIG_CAN 389834")
        # Look for 6 digits
        booking_match = re.search(r'(\d{6})', self.text)
        if booking_match:
            header_data['booking_number'] = booking_match.group(1)

        # 2. Tour Code (e.g., "CHN25A17W1" or "ISL27726A2")
        # Pattern: 3 uppercase, 5+ digits/chars
        tour_code_match = re.search(r'\b([A-Z]{3}\d{5,}[A-Z0-9]*)\b', self.text)
        if tour_code_match:
            header_data['tour_code'] = tour_code_match.group(1)

        # 3. Agent (e.g., "Signet Rep.: kai.hu")
        agent_match = re.search(r'Signet Rep\.:\s*([\w\.]+)', self.text)
        if agent_match:
            header_data['agent_username'] = agent_match.group(1)

        return header_data

    def _extract_passengers(self):
        """
        Extracts list of passengers (Name, Title, DOB, Passport).
        Pattern: "Twin #6 Mr Gho, Bing Tjin (C) Jun 24 1951 (74) SGP K**1710 ..."
        """
        passengers = []
        # Pattern to find passenger rows.
        # Assumes rows start with Room Type (Twin/Single/Double) or Title if Room Type matches previous?
        # Actually, let's look for the specific format: Title Name ... DOB

        # Regex breakdown:
        # (Mr|Mrs|Ms|Mstr|Miss)\s+ -> Title
        # ([A-Z][a-z]+,\s+[\w\s]+?)\s+ -> Name (Last, First Middle) - non-greedy match until DOB
        # (?:\([A-Z]\))?\s* -> Optional Lang code (C)
        # ([A-Z][a-z]{2}\s\d{1,2}\s\d{4}) -> DOB (Jun 24 1951)
        # .*? -> Skip age etc
        # ([A-Z]{3}\s+[A-Z0-9*]+)? -> Optional Passport (SGP K**1710) - greedy?

        # Simplified approach: Split text by lines, look for lines with Title + Date
        lines = self.text.split('\n')
        current_room_type = "Unknown"

        for line in lines:
            line = line.strip()

            # Detect Room Type (heuristic)
            if any(x in line for x in ['Twin #', 'Single #', 'Double #', 'Triple #']):
                current_room_type = line.split()[0] + " " + line.split()[1] # Capture "Twin #6"

            # Detect Passenger Line
            # Look for Title and DOB pattern
            # e.g. "Mr Gho, Bing Tjin (C) Jun 24 1951"
            match = re.search(r'(Mr|Mrs|Ms|Miss|Dr)\s+([A-Za-z,\s]+?)(?:\s*\([A-Z]\))?\s+([A-Z][a-z]{2}\s\d{1,2}\s\d{4})', line)
            if match:
                title = match.group(1)
                name_raw = match.group(2).strip() # Gho, Bing Tjin
                dob_str = match.group(3)

                # Parse Passport if present (Look after DOB)
                # SGP K**1710 or CAN A**5461
                passport_match = re.search(r'([A-Z]{3}\s+[A-Z0-9*]+)\s+[A-Z][a-z]{2}\s\d{4}', line)
                passport = passport_match.group(1) if passport_match else None

                passengers.append({
                    'room_type': current_room_type,
                    'title': title,
                    'name': name_raw,
                    'dob': dob_str,
                    'passport': passport
                })

        return passengers

    def _extract_flights(self):
        """
        Extracts PNR and Flight Segments.
        Pattern 1 (PNR): "PNR 1: GMFVXK (PAX: 2)"
        Pattern 2 (Flight): "Pick Up HU7836 10/17/2025 TAO/TYN 6:00PM - 8:00PM"
        """
        flights = []
        lines = self.text.split('\n')
        current_pnr = None

        for line in lines:
            line = line.strip()

            # 1. PNR Header
            pnr_match = re.search(r'PNR\s*\d*:\s*([A-Z0-9]{6})', line)
            if pnr_match:
                current_pnr = pnr_match.group(1)
                continue

            # 2. Flight Segment
            # HU7836 10/17/2025 TAO/TYN
            flight_match = re.search(r'([A-Z0-9]{2,3}\d{3,4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z]{3}/[A-Z]{3})', line)
            if flight_match:
                code = flight_match.group(1)
                date = flight_match.group(2)
                route = flight_match.group(3)

                flights.append({
                    'pnr': current_pnr,
                    'code': code,
                    'date': date,
                    'route': route,
                    'raw_line': line
                })

        return flights

    def _extract_financials(self):
        """
        Extracts Costs (InvoiceItems) and Payments.
        """
        financials = {
            'items': [],
            'payments': [],
            'coupons': []
        }
        lines = self.text.split('\n')

        # 1. Costs (Top Right usually)
        # "Total: CAD8,900"
        # "A CAD4,450" (Base price)
        # This is hard to robustly parse from raw text stream without coordinates.
        # Fallback: Capture "Total: CAD..."
        total_match = re.search(r'Total:\s*([A-Z]{3})([\d,]+)', self.text)
        if total_match:
            financials['grand_total'] = f"{total_match.group(1)} {total_match.group(2)}"

        # 2. Payments table
        # "Balance CR(CK) CAD900"
        # "Deposit CK CAD2,100"
        for line in lines:
            line = line.strip()

            # Payment Rows
            # Pattern: (Balance|Deposit) ... (CAD|USD)([\d,]+)
            pay_match = re.search(r'(Balance|Deposit)\s+.*\s+([A-Z]{3})([\d,]+)', line)
            if pay_match:
                p_type = pay_match.group(1)
                curr = pay_match.group(2)
                amt = pay_match.group(3).replace(',', '')
                # Avoid "Total Paid" summary lines if possible, or filter duplicates later
                financials['payments'].append({
                    'type': p_type,
                    'amount': amt, # stored as string for JSON serialization
                    'currency': curr,
                    'raw_line': line
                })

            # Coupon Rows
            # "Discount ... CAD178"
            # "Coupon SY-ES... CAD130"
            if line.startswith('Discount') or line.startswith('Coupon'):
                # Try to extract amount
                amt_match = re.search(r'([A-Z]{3})([\d,]+)', line)
                if amt_match:
                    code_match = re.search(r'(SY-[A-Z0-9-]+)', line)
                    code = code_match.group(1) if code_match else "General Discount"
                    amt = amt_match.group(2).replace(',', '')

                    financials['coupons'].append({
                        'code': code,
                        'amount': amt, # stored as string
                        'currency': amt_match.group(1)
                    })

        return financials

    def close(self):
        if self.doc:
            self.doc.close()
