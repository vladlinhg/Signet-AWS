
import unittest
import re
from decimal import Decimal

class MockPDFParser:
    def __init__(self, text):
        self.text = text

    def extract_tour_code(self):
        # Broaden regex to catch ISL27726A2 (3 letters, 5+ digits, chars)
        match = re.search(r"\b([A-Z]{3}\d{5,}[A-Z0-9]*)\b", self.text)
        if match:
            return match.group(1)
        return None

    def extract_passengers(self):
        passengers = []

        # 1. Titles
        titles = re.findall(r"\b(Mr|Mrs|Ms|Miss|Dr|Mstr)\b", self.text)

        # 2. Names (Last, First)
        raw_names = re.findall(r"([A-Z][a-z]+),\s*\n?([A-Z][a-z]+)", self.text)
        names = []
        for last, first in raw_names:
            if last == "Last" and first == "First": continue # Header
            names.append(f"{last}, {first}")

        # 3. DOBs (Oct 11 1962)
        # Regex to capture Year group
        # Match 'Mmm DD YYYY'
        raw_dates = re.findall(r"(([A-Z][a-z]{2})\s(\d{1,2})\s(\d{4}))", self.text)
        dobs = []
        for full_date, month, day, year in raw_dates:
            if int(year) > 2025: continue # Skip Expiry Dates
            dobs.append(full_date)

        # Zip them safely (stop at shortest list)
        count = min(len(titles), len(names), len(dobs))

        for i in range(count):
            passengers.append({
                'title': titles[i],
                'name': names[i],
                'dob': dobs[i]
            })

        return passengers

    def extract_financials(self):
        balance = Decimal(0)
        # Current Logic
        match = re.search(r"Balance\s+([A-Z]{3})?([\d,\.]+)", self.text)
        if match:
             val_str = match.group(2).replace(',', '')
             balance = Decimal(val_str)
        return {'balance': balance}

class TestPDFRegex(unittest.TestCase):
    def setUp(self):
        self.raw_text = """
=== Page 1 ===
NET
Submissions
OBS
Settings
esther.lin
Logoff
Total:
CAD0
Total:
CAD0
Total:
CAD0
Total:
-CAD0
SIG_CAN  405140
02/05/2026
Group No.
 Update: (02/05/2026)
2
New Booking
2
Deposited (Due by 02/10/2026)
3
Invoice
4
Travel Doc
5
Guide's greeting
6
Completed
CAD464 (2%) off land total paid by check

Request
Title
Last, First/Middle
DOB
Passport/ID
Exp.Date
Meals Res
Motion Sickness
Insurance
Remark
Prices
 #3
Mr
(M)
Oct 11 1962 (64)
CAN P**14NG
Jun 13 2034
A CAD11,600
Ms
(M)
Oct 20 1963 (63)
CAN P**18NG
Jun 13 2034
A CAD11,600
Twin
Zhu,
Zhongwen
N/A
N/A
Xu, Hong
N/A
N/A
Total: CAD23,200
Pick-up / Send-off

/
 /
P/U List S/O List
Flight info
Hotel Ext. (0) - Pre Post
Pre: No Hotel
Items
# RM
RM type
Guests
# Nt
Rate/R/N
Ch-in
Ch-out
Remark
Submit
Handler
Action
Status
Subtotal
Optional (0)
Items
$ / Adt
# of Adt
$ / Chd
# of Chd
Remark
Submit
Handler
Action
Status
Subtotal
Others (0)
Items
Amount
Count
Remark
Submit
Handler
Action
Status
Subtotal
Concession (0)
Items
Ref #
Amount
Count
Remark
Submit
Handler
Action
Status
Subtotal
New OBS
 Contact
Mr. Zhu, Zhongwen
+1 (514) 298-3852
zhongwen.zhu@gmail.com
Contact info:
冰島環島風情遊11天10夜 ISL27726A2 (R12/3, G4/0)
Tour starts/ends: 07/26/2027 KEF - 08/05/2027 KEF
Tour Language: M
Signet Rep.: kai.hu





2/7/26, 2:07 PM
超值旅游后台管理系统 - OBS
https://new.supernettours.com/obs_queryBookingDetail.do?bkrId=405140
1/2

=== Page 2 ===
Grand Total
CAD23,200
Total Paid:
-CAD4,400
Balance  CAD18,800




Payment (1)
Items
FOP
# / sabre
Amount
Counts
Remark
Submit
Handler
Action
Status
Subtotal
Deposit
CC
GUMYYP
CAD4,400
2
Credit Card
System
Lisa
CFM
CAD4,400
CXL
-
Revise booking
Revise booking
Preview
Preview
PreTour Remind/Itin
Group Invitation
After tour greeting
After tour greeting
Note
External Note
Add Note
Internal Note
Add Note
Logs
History (5)
PDF Doc. (2)
Check List. (0)
1
Date/Time
Type
Description
By
02/06/2026 10:24AM
Online Payment
Deposit has been Approved. Remark: Auth04204I
Lisa.Chen
02/06/2026 10:24AM
Status
Status Changed: from New Booking to Deposited
System
02/06/2026 10:11AM
Cust. Profile
Update: Hong, Xu
Kai.Hu
02/06/2026 10:11AM
Cust. Profile
Update: Zhongwen, Zhu
Kai.Hu
02/05/2026 12:58PM
New Booking
From Online Submission
System





2/7/26, 2:07 PM
超值旅游后台管理系统 - OBS
https://new.supernettours.com/obs_queryBookingDetail.do?bkrId=405140
2/2
        """

    def test_tour_code(self):
        print("\\n--- Testing Tour Code ---")
        parser = MockPDFParser(self.raw_text)
        code = parser.extract_tour_code()
        print(f"Tour Code Found: {code}")
        self.assertEqual(code, "ISL27726A2")

    def test_financials(self):
        print("\\n--- Testing Financials ---")
        parser = MockPDFParser(self.raw_text)
        fin = parser.extract_financials()
        print(f"Balance Found: {fin['balance']}")
        self.assertEqual(fin['balance'], 18800)

    def test_passengers(self):
        print("\\n--- Testing Passengers ---")
        parser = MockPDFParser(self.raw_text)
        pax = parser.extract_passengers()
        print(f"Passengers Found: {len(pax)}")
        for p in pax:
            print(f" - {p}")

        self.assertEqual(len(pax), 2)
        # Check alignment
        # 1st Pax: Mr (Title 0), Zhu (Name 0), Oct 11 1962 (DOB 0)
        self.assertEqual(pax[0]['title'], "Mr")
        self.assertEqual(pax[0]['name'], "Zhu, Zhongwen")
        self.assertEqual(pax[0]['dob'], "Oct 11 1962")

        # 2nd Pax: Ms (Title 1), Xu (Name 1), Oct 20 1963 (DOB 1)
        self.assertEqual(pax[1]['title'], "Ms")
        self.assertEqual(pax[1]['name'], "Xu, Hong")
        self.assertEqual(pax[1]['dob'], "Oct 20 1963")

if __name__ == "__main__":
    unittest.main()
