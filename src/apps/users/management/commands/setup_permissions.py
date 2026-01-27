from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import User
from apps.sales.models import Invoice, InvoiceItem
from apps.clients.models import Client
from apps.flights.models import Flight, FlightTicket
from apps.tours.models import Product, TourInstance
from apps.currencies.models import Currency

class Command(BaseCommand):
    help = 'Setup default groups and permissions based on Roles'

    def handle(self, *args, **options):
        self.stdout.write("Setting up Permissions...")
        
        # 1. Define Groups
        groups = {
            User.Role.IT_ADMIN: [], # Superuser gets everything
            User.Role.MANAGER: ['view', 'change', 'add', 'delete'], # All Access
            User.Role.ACCOUNTANT: ['view_invoice', 'change_invoice', 'view_client'],
            User.Role.SALES: ['add_invoice', 'change_invoice', 'view_invoice', 'view_client', 'add_client', 'change_client', 'view_flight', 'view_tourinstance', 'view_product'],
            User.Role.MARKETING: ['view_invoice', 'view_client', 'view_product', 'view_tourinstance'] 
        }

        # Helper to get permissions
        def get_perms(model, actions):
            ct = ContentType.objects.get_for_model(model)
            perms = []
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"
                try:
                    p = Permission.objects.get(content_type=ct, codename=codename)
                    perms.append(p)
                except Permission.DoesNotExist:
                    print(f"Warning: Permission {codename} not found.")
            return perms

        # 2. Configure Groups
        
        # --- MANAGER ---
        g_mgr, _ = Group.objects.get_or_create(name='Manager')
        # Manager gets almost everything - simplified here by just giving them super-ish powers or specific list
        # For simplicity, let's give them all on core apps
        for model in [Invoice, InvoiceItem, Client, Flight, FlightTicket, Product, TourInstance, Currency, User]:
            g_mgr.permissions.add(*get_perms(model, ['view', 'add', 'change', 'delete']))
            
        # --- ACCOUNTANT ---
        g_acc, _ = Group.objects.get_or_create(name='Accountant')
        g_acc.permissions.add(*get_perms(Invoice, ['view', 'change']))
        g_acc.permissions.add(*get_perms(InvoiceItem, ['view', 'change']))
        g_acc.permissions.add(*get_perms(Client, ['view']))
        
        # --- SALES ---
        g_sales, _ = Group.objects.get_or_create(name='Sales')
        g_sales.permissions.add(*get_perms(Invoice, ['view', 'add', 'change']))
        g_sales.permissions.add(*get_perms(InvoiceItem, ['view', 'add', 'change', 'delete']))
        g_sales.permissions.add(*get_perms(Client, ['view', 'add', 'change']))
        g_sales.permissions.add(*get_perms(Flight, ['view']))
        g_sales.permissions.add(*get_perms(Product, ['view']))
        g_sales.permissions.add(*get_perms(TourInstance, ['view']))

        # --- MARKETING ---
        g_mkt, _ = Group.objects.get_or_create(name='Marketing')
        g_mkt.permissions.add(*get_perms(Invoice, ['view']))
        g_mkt.permissions.add(*get_perms(InvoiceItem, ['view']))
        g_mkt.permissions.add(*get_perms(Client, ['view']))
        g_mkt.permissions.add(*get_perms(Product, ['view']))
        g_mkt.permissions.add(*get_perms(TourInstance, ['view']))
        
        print("Groups Configured.")

        # 3. Assign Users to Groups
        print("Assigning Users to Groups...")
        for user in User.objects.all():
            if user.role == User.Role.MANAGER:
                user.groups.add(g_mgr)
            elif user.role == User.Role.ACCOUNTANT:
                user.groups.add(g_acc)
            elif user.role == User.Role.SALES:
                user.groups.add(g_sales)
            elif user.role == User.Role.MARKETING:
                user.groups.add(g_mkt)
            elif user.role == User.Role.IT_ADMIN:
                user.is_superuser = True
                user.is_staff = True
                user.save()
        
        print("Done.")
