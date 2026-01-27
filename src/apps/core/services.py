import csv
import io
from django.utils.dateparse import parse_date
from apps.users.models import User
from apps.tours.models import Product, TourInstance
from apps.currencies.models import Currency, ExchangeRate
from django.utils import timezone
from apps.flights.models import Flight
from apps.clients.models import Client

class DataImportService:
    def parse_csv(self, file_obj, import_type):
        """
        Parses CSV and returns a list of dictionaries with 'data' and 'status' (NEW/DUPLICATE).
        Does NOT save to DB.
        """
        # Ensure we are at start
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            
        decoded_file = file_obj.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        preview_data = []
        
        for row in reader:
            item = {'data': row, 'status': 'NEW'}
            
            if import_type == 'clients':
                if Client.objects.filter(first_name=row['first'], last_name=row['last']).exists():
                    item['status'] = 'DUPLICATE'
                    
            elif import_type == 'flights':
                # Check based on Flight Code factors
                # {Airline}{FlightNum}{Date}{Dept}
                airline = row['airline']
                flight_no = row['flight_no']
                dept = row['dept']
                dates = row['dates'].split('|')
                
                # If ANY date exists, mark row as partial duplicate or duplicate?
                # Simply check if the FIRST date exists for now, or just Flag if any combo exists.
                # Since one row = multiple flights, let's just check the first one for simplicity 
                # or expand the row into multiple preview items.
                # Expanding is better.
                pass 
                
            elif import_type == 'tours':
                # Check Product Code Factors
                if Product.objects.filter(country_code=row['country'], unique_seq=row['unique']).exists():
                    item['status'] = 'DUPLICATE (Product)'
            
            elif import_type == 'users':
                if User.objects.filter(username=row['username']).exists():
                    item['status'] = 'DUPLICATE'

            elif import_type == 'currencies':
                if Currency.objects.filter(code=row['code']).exists():
                    item['status'] = 'DUPLICATE'
            
            preview_data.append(item)
            
        # Special handling for Flights (One row -> Multiple Dates)
        if import_type == 'flights':
            expanded_data = []
            for item in preview_data:
                row = item['data']
                dates = row['dates'].split('|')
                for dt in dates:
                    # Check Logic
                    is_dup = False
                    dt_obj = parse_date(dt)
                    if dt_obj:
                         # Reconstruct what the code WOULD be, or just query fields
                         if Flight.objects.filter(airline_code=row['airline'], flight_number=row['flight_no'], departure_date=dt_obj).exists():
                             is_dup = True
                    
                    new_item = {
                        'data': {
                            'airline': row['airline'],
                            'flight_no': row['flight_no'],
                            'dept': row['dept'],
                            'arr': row['arr'],
                            'date': dt
                        },
                        'status': 'DUPLICATE' if is_dup else 'NEW'
                    }
                    expanded_data.append(new_item)
            return expanded_data

        return preview_data

    def save_data(self, data_list, import_type):
        """
        Saves the selected data.
        data_list: list of dicts (from the preview stage)
        """
        count = 0
        for row in data_list:
            if import_type == 'clients':
                Client.objects.get_or_create(
                    first_name=row['first'],
                    last_name=row['last'],
                    defaults={
                        'email': row['email'],
                        'phone': row['phone']
                        # Add Doc handling if needed, simplified here
                    }
                )
                count += 1
            elif import_type == 'flights':
                dt = parse_date(row['date'])
                if dt:
                    Flight.objects.get_or_create(
                        airline_code=row['airline'],
                        flight_number=row['flight_no'],
                        departure_date=dt,
                        departure_airport=row['dept'],
                        defaults={'arrival_airport': row['arr']}
                    )
                    count += 1
            elif import_type == 'tours':
                 # Create Product
                prod, _ = Product.objects.get_or_create(
                    name=row['name'],
                    defaults={
                        'country_code': row['country'],
                        'days_count': row['days'],
                        'unique_seq': row['unique']
                    }
                )
                # Instances
                dates = row['start_dates'].split('|')
                for dt_str in dates:
                    dt = parse_date(dt_str)
                    if dt:
                        TourInstance.objects.get_or_create(
                            product=prod,
                            start_date=dt,
                            defaults={'end_date': dt, 'total_spots': 20}
                        )

                count += 1
            
            elif import_type == 'users':
                if not User.objects.filter(username=row['username']).exists():
                    u = User.objects.create_user(
                        username=row['username'],
                        password=row['password'],
                        email=row['email'],
                        role=row['role'],
                        is_staff=True # Allow Admin Panel Access
                    )
                    if row['role'] == 'IT_ADMIN':
                        u.is_superuser = True
                        u.save()
                    count += 1

            elif import_type == 'currencies':
                curr, _ = Currency.objects.get_or_create(
                    code=row['code'],
                    defaults={
                        'name': row['name'],
                        'symbol': row['symbol']
                    }
                )
                # Create Rate
                ExchangeRate.objects.get_or_create(
                    currency=curr,
                    date=timezone.now().date(),
                    defaults={'rate_to_base': row['rate_to_cad']}
                )
                count += 1
        return count

class DataImporter:
    """
    Wrapper for Backward Compatibility with Management Command.
    """
    def process_csv(self, file_obj, import_type):
        service = DataImportService()
        # Parse
        preview_data = service.parse_csv(file_obj, import_type)
        # Extract data parts
        to_save = [item['data'] for item in preview_data]
        # Save
        return service.save_data(to_save, import_type)
