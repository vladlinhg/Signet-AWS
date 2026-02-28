import os
import sys
import django
import logging
from io import BytesIO

# Setup Django environment
sys.path.insert(0, '/app')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from apps.core.services.imports.pdf_parser import PDFParserService
from apps.core.services.imports.normalize.main import normalize_booking_text
from apps.core.services.imports.db_sync.main import BookingImportService

from apps.tours.models import Product, TourInstance, TourBooking
from apps.flights.models import Airline, Airport, Flight, FlightInstance, FlightTicket
from apps.clients.models import Client, TravelDocument
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment, InvoiceNote
from django.contrib.auth import get_user_model

User = get_user_model()

class AssertionEngine:
    def __init__(self, raw_json: dict, booking_number: str):
        self.data = raw_json
        self.bk = booking_number
        self.errors = []
        self.invoice = None

    def fail(self, msg: str):
        self.errors.append(msg)
        print(f"    [X] FAIL: {msg}")

    def ok(self, msg: str):
        print(f"    [✔] OK: {msg}")

    def run(self):
        print("\n========================================")
        print("=     DATABASE ASSERTION ENGINE        =")
        print("========================================\n")
        
        self.assert_users()
        self.assert_level_1()
        self.assert_level_2()
        self.assert_level_3()
        
        if not self.errors:
            print("\n========================================")
            print("=  ALL ASSERTIONS PASSED PERFECTLY!    =")
            print("========================================")
        else:
            print("\n========================================")
            print(f"=  FAILED WITH {len(self.errors)} DISCREPANCIES   =")
            print("========================================")

    def assert_users(self):
        print("-> Asserting System Users...")
        # Check sales user
        sales_str = self.data['invoice']['fields'].get('sales_user_username')
        if sales_str:
            if User.objects.filter(username=sales_str).exists():
                self.ok(f"Sales Rep User ({sales_str}) exists.")
            else:
                self.fail(f"Sales Rep User ({sales_str}) MISSING from DB.")
                
        # Check authors
        for note in self.data.get('invoice_notes', []):
            author_str = note['author']['fields'].get('username')
            if author_str and not User.objects.filter(username=author_str).exists():
                self.fail(f"Author User ({author_str}) MISSING from DB.")
        self.ok("All Note Authors exist.")

    def assert_level_1(self):
        print("\n-> Asserting Level 1 (Base Entities)...")
        for apt in self.data.get('airports', []):
            code = apt['lookup_key'].get('iata_code') or apt['lookup_key'].get('code')
            if Airport.objects.filter(code=code).exists():
                self.ok(f"Airport {code} verified.")
            else:
                self.fail(f"Airport {code} MISSING.")
                
        for al in self.data.get('airlines', []):
            code = al['lookup_key']['code']
            if Airline.objects.filter(code=code).exists():
                self.ok(f"Airline {code} verified.")
            else:
                self.fail(f"Airline {code} MISSING.")
                
        for flt in self.data.get('flights', []):
            fn = flt['fields']['flight_number']
            lk = flt['lookup_key']
            dep = lk.get('departure_airport_iata') or lk.get('departure_airport')
            arr = lk.get('arrival_airport_iata') or lk.get('arrival_airport')
            if Flight.objects.filter(airline__code=lk['airline_code'], flight_number=fn, departure_airport__code=dep, arrival_airport__code=arr).exists():
                self.ok(f"Base Flight {lk['airline_code']}{fn} verified.")
            else:
                self.fail(f"Base Flight {lk['airline_code']}{fn} MISSING.")

        ti = self.data.get('tour_instance')
        if ti:
            tc = ti['fields']['tour_code']
            if TourInstance.objects.filter(tour_code=tc, language=ti['fields']['language']).exists():
                self.ok(f"Tour Instance {tc} verified.")
            else:
                self.fail(f"Tour Instance {tc} MISSING.")

    def assert_level_2(self):
        print("\n-> Asserting Level 2 (Complex Connections)...")
        # Invoice
        try:
            self.invoice = Invoice.objects.get(booking_number=self.bk)
            inv_f = self.data['invoice']['fields']
            if self.invoice.status == inv_f['status'] and self.invoice.group_no == str(inv_f.get('group_no', '')):
                self.ok(f"Invoice {self.bk} verified.")
            else:
                self.fail(f"Invoice {self.bk} mapped incorrectly.")
        except Invoice.DoesNotExist:
            self.fail(f"Invoice {self.bk} MISSING.")
            return

        # Flight Instances
        for fi in self.data.get('flight_instances', []):
            code = fi['fields']['flight_code']
            if FlightInstance.objects.filter(flight_code=code, departure_date=fi['fields']['departure_date']).exists():
                self.ok(f"Flight Instance {code} verified.")
            else:
                self.fail(f"Flight Instance {code} MISSING.")

        # Clients
        for cli in self.data.get('clients', []):
            flds = cli['fields']
            fn, ln = flds['first_name'], flds['last_name']
            
            qs = Client.objects.filter(first_name=fn, last_name=ln, birth_date=flds.get('birth_date'))
            if qs.exists():
                db_client = qs.first()
                self.ok(f"Client {fn} {ln} verified.")
                # Health
                hp = cli.get('health_plan', {})
                if hp:
                    dr = hp.get('dietary_restrictions', {}).get('incoming')
                    al = hp.get('allergies', {}).get('incoming')
                    if dr and db_client.dietary_restrictions != dr:
                        self.fail(f"Client {fn} {ln} Dietary mismatch.")
                    if al and db_client.allergies != al:
                        self.fail(f"Client {fn} {ln} Allergy mismatch.")
            else:
                self.fail(f"Client {fn} {ln} MISSING.")

    def assert_level_3(self):
        print("\n-> Asserting Level 3 (Ledger & Dependents)...")
        if not self.invoice:
            self.fail("Cannot verify Level 3 without root Invoice.")
            return

        for cli in self.data.get('clients', []):
            flds = cli['fields']
            db_client = Client.objects.filter(first_name=flds['first_name'], last_name=flds['last_name']).first()
            if not db_client: continue

            # Documents
            for doc in cli.get('travel_documents', []):
                dn = doc['doc_number']
                if TravelDocument.objects.filter(client=db_client, doc_number=dn).exists():
                    self.ok(f"Passport {dn} attached to {flds['first_name']}.")
                else:
                    self.fail(f"Passport {dn} MISSING for {flds['first_name']}.")

            # Flight Tickets
            for tkt in cli.get('flight_tickets', []):
                tc = tkt['ticket_code']
                if FlightTicket.objects.filter(client=db_client, ticket_code=tc, pnr=tkt['pnr']).exists():
                    self.ok(f"Ticket {tc} attached to {flds['first_name']}.")
                else:
                    self.fail(f"Ticket {tc} MISSING for {flds['first_name']}.")

        # Ledger Math
        db_items_count = InvoiceItem.objects.filter(invoice=self.invoice).count()
        json_items_count = len(self.data.get('invoice_items', []))
        if db_items_count == json_items_count:
            self.ok(f"InvoiceItems count matched ({db_items_count}).")
        else:
            self.fail(f"InvoiceItems count mismatch: JSON {json_items_count} vs DB {db_items_count}")

        db_pmt_count = InvoicePayment.objects.filter(invoice=self.invoice).count()
        json_pmt_count = len(self.data.get('payments', []))
        if db_pmt_count == json_pmt_count:
            self.ok(f"InvoicePayments count matched ({db_pmt_count}).")
        else:
            self.fail(f"InvoicePayments count mismatch: JSON {json_pmt_count} vs DB {db_pmt_count}")

        db_notes_count = InvoiceNote.objects.filter(invoice=self.invoice).count()
        json_notes_count = len(self.data.get('invoice_notes', []))
        if db_notes_count == json_notes_count:
            self.ok(f"InvoiceNotes count matched ({db_notes_count}).")
        else:
            self.fail(f"InvoiceNotes count mismatch: JSON {json_notes_count} vs DB {db_notes_count}")

def verify(pdf_path: str):
    print(f"[*] Uploading: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    
    parser = PDFParserService(BytesIO(file_bytes))
    booking_no = parser.extract_booking_number_only()
    print(f"[*] Found Booking Number: {booking_no}")
    
    byte_stream = BytesIO(file_bytes)
    byte_stream.seek(0)
    parser.parse()
    
    # 1. GENERATE JSON PAYLOAD
    normalized_payload = normalize_booking_text(booking_no, parser.text)
    
    # 2. RUN SYNC TO DATABASE
    print(f"\n[*] Executing DB Sync on Normalized Structure...")
    
    # Force delete the invoice to bypass the anti-thrashing Duplicate Checker
    Invoice.objects.filter(booking_number=booking_no).delete()
    
    importer = BookingImportService(normalized_payload, dry_run=False, file_bytes=file_bytes, filename="test_344565.pdf")
    importer.execute()
    
    # 3. ASSERTION
    engine = AssertionEngine(normalized_payload, booking_no)
    engine.run()

if __name__ == "__main__":
    test_pdf = "/app/media/supporting_documents/test_344565.pdf"
    verify(test_pdf)
