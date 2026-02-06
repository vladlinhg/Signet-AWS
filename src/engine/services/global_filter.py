import datetime
from datetime import timedelta
from django.utils import timezone
from apps.invoices.models import Invoice
from apps.currencies.models import Currency

class GlobalFilterService:
    def __init__(self, request):
        self.request = request
        self.params = request.GET
        self.today = timezone.now().date()

    def get_context(self):
        """
        Process request and return a unified context dictionary for filtering.
        Returns:
            dict: Context with dates, offsets, selections, and querysets.
        """
        # 1. Basic Selections
        selected_currency_code = self.params.get('currency', 'CAD')
        calc_mode = self.params.get('mode', 'actual') # Default actual? Or check previous usage. Marketing was 'actual', Manager was 'anticipated'. Let's standardize to 'actual' per user latest request on Marketing.

        # 2. Status Selection
        selected_statuses = self.params.getlist('status')
        if not selected_statuses:
             # Default to ALL if hidden/empty
             selected_statuses = Invoice.Status.values

        # 3. Date Logic (Prioritize Month Offset -> Manual Dates)
        month_offset = self.params.get('month_offset')
        date_from_str = self.params.get('date_from')
        date_to_str = self.params.get('date_to')

        start_date = None
        end_date = None
        current_month_label = "Custom Range"

        if month_offset is not None:
            try:
                offset = int(month_offset)
                # Reference: Today's Month Start
                curr_month_start = self.today.replace(day=1)

                # Target Month logic
                total_months = curr_month_start.year * 12 + (curr_month_start.month - 1) + offset
                target_year = total_months // 12
                target_month = (total_months % 12) + 1

                start_date = datetime.date(target_year, target_month, 1)

                # End Date logic
                next_total = total_months + 1
                next_year = next_total // 12
                next_month = (next_total % 12) + 1
                next_month_start = datetime.date(next_year, next_month, 1)
                end_date = next_month_start - timedelta(days=1)

                # Update strings
                date_from_str = start_date.strftime('%Y-%m-%d')
                date_to_str = end_date.strftime('%Y-%m-%d')

                current_month_label = start_date.strftime('%B %Y')

            except ValueError:
                pass
        else:
            # Manual Dates
            if date_from_str:
                try:
                    start_date = datetime.datetime.strptime(date_from_str, '%Y-%m-%d').date()
                except ValueError: pass
            if date_to_str:
                try:
                    end_date = datetime.datetime.strptime(date_to_str, '%Y-%m-%d').date()
                except ValueError: pass

            # All Time Override
            all_time = self.params.get('all_time')
            if all_time == 'on':
                start_date = None
                end_date = None
                current_month_label = "All Time"
                month_offset = None # Clear offset context

            # If no dates, no offset, and NOT all_time? Default to Current Month (Offset 0)
            elif not start_date and not end_date:
                month_offset = 0
                curr_month_start = self.today.replace(day=1)
                # ... same default logic ...
                total_months = curr_month_start.year * 12 + (curr_month_start.month - 1)
                target_year = total_months // 12
                target_month = (total_months % 12) + 1
                start_date = datetime.date(target_year, target_month, 1)

                next_total = total_months + 1
                next_year = next_total // 12
                next_month = (next_total % 12) + 1
                next_month_start = datetime.date(next_year, next_month, 1)
                end_date = next_month_start - timedelta(days=1)

                date_from_str = start_date.strftime('%Y-%m-%d')
                date_to_str = end_date.strftime('%Y-%m-%d')
                current_month_label = start_date.strftime('%B %Y')
                start_date = curr_month_start
                # End of current month
                if curr_month_start.month == 12:
                    end_date = datetime.date(curr_month_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime.date(curr_month_start.year, curr_month_start.month + 1, 1) - timedelta(days=1)

                date_from_str = start_date.strftime('%Y-%m-%d')
                date_to_str = end_date.strftime('%Y-%m-%d')
                current_month_label = start_date.strftime('%B %Y')


        # 4. Data Assets
        available_currencies = Currency.objects.filter(invoice__isnull=False).distinct()
        available_statuses = Invoice.Status.values

        return {
            # Filter Values
            'selected_currency_code': selected_currency_code,
            'calc_mode': calc_mode,
            'selected_statuses': selected_statuses,

            # Date Values
            'date_from': date_from_str,
            'date_to': date_to_str,
            'start_date': start_date, # Date Objects for Querying
            'end_date': end_date,
            'month_offset': month_offset,
            'current_month_label': current_month_label,

            # Options
            'available_currencies': available_currencies,
            'available_statuses': available_statuses,
        }
