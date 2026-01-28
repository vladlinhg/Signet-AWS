import os
import django
import sys

# Setup Django
sys.path.append('d:/Signet/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tours.models import Product, TourInstance, TourBooking

def check_models():
    print("Checking Products...")
    for p in Product.objects.all():
        try:
            s = str(p)
            c = p.code
            print(f"Product OK: {s}")
        except Exception as e:
            print(f"CRASH Product {p.pk}: {e}")

    print("\nChecking TourInstances...")
    for ti in TourInstance.objects.all():
        try:
            s = str(ti)
            print(f"TourInstance OK: {s}")
        except Exception as e:
            print(f"CRASH TourInstance {ti.pk}: {e}")

    print("\nChecking TourBookings...")
    for tb in TourBooking.objects.all():
        try:
            s = str(tb)
            print(f"TourBooking OK: {s}")
        except Exception as e:
            print(f"CRASH TourBooking {tb.pk}: {e}")

if __name__ == '__main__':
    try:
        check_models()
        print("\nAll checks completed.")
    except Exception as e:
        print(f"Fatal Script Error: {e}")
