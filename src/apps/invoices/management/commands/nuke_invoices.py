from django.core.management.base import BaseCommand
from apps.invoices.models import Invoice, InvoiceItem

class Command(BaseCommand):
    help = 'Deletes all Invoices and InvoiceItems'

    def handle(self, *args, **options):
        self.stdout.write('Nuking Invoices...')
        count_items = InvoiceItem.objects.all().delete()[0]
        count_invoices = Invoice.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f'Deleted {count_invoices} Invoices and {count_items} Items.'))
