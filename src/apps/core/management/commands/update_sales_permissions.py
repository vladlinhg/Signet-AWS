from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from apps.invoices.models import InvoicePayment, AddonService, Coupon
from apps.documents.models import SupportingDocument
from apps.tours.models import TourBooking, TourInstance, Product
from apps.flights.models import FlightTicket, Flight, FlightInstance, Airline, Airport

User = get_user_model()

class Command(BaseCommand):
    help = 'Update Permissions for Sales Group (Payments, Docs, Bookings)'

    def handle(self, *args, **options):
        self.stdout.write("Updating Sales Permissions...")

        # 1. Create/Get Sales Group
        sales_group, created = Group.objects.get_or_create(name='Sales')
        if created:
            self.stdout.write("  - Created 'Sales' Group")
        else:
            self.stdout.write("  - Found 'Sales' Group")

        # 2. Define Permissions to Grant
        # Model -> List of codenames (prefixes)
        models_perms = [
            (InvoicePayment, ['add', 'change', 'view', 'delete']),
            (SupportingDocument, ['add', 'change', 'view', 'delete']),
            (TourBooking, ['add', 'change', 'view', 'delete']),
            (TourInstance, ['add', 'change', 'view', 'delete']),
            (Product, ['add', 'change', 'view', 'delete']),
            (FlightTicket, ['add', 'change', 'view', 'delete']),
            (FlightInstance, ['add', 'change', 'view', 'delete']),
            (Flight, ['add', 'change', 'view', 'delete']),
            (Airline, ['add', 'change', 'view', 'delete']),
            (Airport, ['add', 'change', 'view', 'delete']),
            (AddonService, ['add', 'change', 'view', 'delete']),
            (Coupon, ['add', 'change', 'view', 'delete']),
        ]

        perms_to_add = []
        for model_cls, ops in models_perms:
            ct = ContentType.objects.get_for_model(model_cls)
            for op in ops:
                codename = f"{op}_{model_cls._meta.model_name}"
                try:
                    p = Permission.objects.get(content_type=ct, codename=codename)
                    perms_to_add.append(p)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"    ! Warning: Permission {codename} not found"))

        # 3. Assign Permissions
        sales_group.permissions.add(*perms_to_add)
        self.stdout.write(f"  - Granted {len(perms_to_add)} permissions to Sales Group")

        # 4. Assign Users to Group
        sales_users = User.objects.filter(role='SALES')
        for u in sales_users:
            u.groups.add(sales_group)
            u.save()

        self.stdout.write(f"  - Added {sales_users.count()} users to Sales Group")
        self.stdout.write(self.style.SUCCESS('Permissions Updated Successfully.'))
