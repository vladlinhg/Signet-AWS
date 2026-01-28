import os
import django
import sys

# Setup Django Environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.clients.models import City, Ethnicity
from apps.flights.models import Airport

def run():
    print("Seeding Reference Data...")

    # 1. Hometown Cities
    cities_data = {
        "metro_vancouver": [
            "Vancouver", "Richmond", "Burnaby", "Surrey", "Coquitlam",
            "New Westminster", "North Vancouver", "West Vancouver", "Delta",
            "Langley", "Port Coquitlam", "Port Moody", "Maple Ridge"
        ],
        "canada_other": [
            "Toronto", "Mississauga", "Brampton", "Markham", "Scarborough",
            "Ottawa", "Montreal", "Laval", "Calgary", "Edmonton",
            "Winnipeg", "Hamilton", "Kitchener", "Waterloo", "Guelph",
            "London (ON)", "Victoria", "Nanaimo", "Kelowna", "Kamloops",
            "Prince George"
        ],
        "international": [
            "Hong Kong", "Shanghai", "Beijing", "Shenzhen", "Guangzhou",
            "Taipei", "Kaohsiung", "Seoul", "Busan", "Tokyo", "Osaka",
            "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
            "Lahore", "Karachi", "Dhaka", "Manila", "Cebu",
            "Ho Chi Minh City", "Hanoi", "Bangkok", "Jakarta",
            "London", "Manchester", "Paris", "Berlin", "Frankfurt",
            "Rome", "Milan", "Madrid", "Barcelona", "Amsterdam",
            "Tehran", "Dubai", "Abu Dhabi", "Cairo", "Johannesburg",
            "Los Angeles", "San Francisco", "Seattle", "New York City",
            "Chicago", "Mexico City", "São Paulo"
        ]
    }

    for category, city_list in cities_data.items():
        country = "CA" if category in ["metro_vancouver", "canada_other"] else ""
        for city_name in city_list:
            City.objects.get_or_create(
                name=city_name,
                defaults={'country_code': country}
            )
    print(f"Seeded {City.objects.count()} Cities.")

    # 2. Ethnicity
    ethnicity_data = {
        "broad_categories": [
            "Indigenous (First Nations, Métis, Inuit)", "White / European",
            "East Asian", "South Asian", "Southeast Asian", "Middle Eastern",
            "African", "Latin American", "Mixed / Multiple Ethnicities",
            "Other", "Prefer not to say"
        ],
        "detailed_options": [
            "Chinese", "Indian", "Punjabi", "Pakistani", "Filipino",
            "Korean", "Japanese", "Vietnamese", "Iranian / Persian",
            "Arab", "Jewish", "Ukrainian", "Russian", "Polish",
            "Italian", "German", "French", "British", "Irish",
            "Mexican", "Brazilian", "Colombian", "Nigerian",
            "Ethiopian"
        ]
    }

    # Combine and deduplicate
    all_ethnicities = set(ethnicity_data["broad_categories"] + ethnicity_data["detailed_options"])
    for eth_name in all_ethnicities:
        Ethnicity.objects.get_or_create(name=eth_name)
    print(f"Seeded {Ethnicity.objects.count()} Ethnicities.")

    # 3. Frequent Airports
    airports_data = {
        "primary": [
            { "code": "YVR", "name": "Vancouver International Airport" },
            { "code": "YXX", "name": "Abbotsford International Airport" }
        ],
        "canada_nearby": [
            { "code": "YYJ", "name": "Victoria International Airport" },
            { "code": "YCD", "name": "Nanaimo Airport" },
            { "code": "YKA", "name": "Kamloops Airport" },
            { "code": "YLW", "name": "Kelowna International Airport" }
        ],
        "us_cross_border": [
            { "code": "BLI", "name": "Bellingham International Airport" },
            { "code": "SEA", "name": "Seattle–Tacoma International Airport" },
            { "code": "PAE", "name": "Paine Field (Everett)" }
        ],
        "international_hubs": [
            { "code": "HKG", "name": "Hong Kong International Airport" },
            { "code": "ICN", "name": "Incheon International Airport" },
            { "code": "NRT", "name": "Tokyo Narita International Airport" },
            { "code": "HND", "name": "Tokyo Haneda Airport" },
            { "code": "LAX", "name": "Los Angeles International Airport" },
            { "code": "SFO", "name": "San Francisco International Airport" },
            { "code": "ORD", "name": "Chicago O'Hare International Airport" },
            { "code": "JFK", "name": "John F. Kennedy International Airport" },
            { "code": "LHR", "name": "London Heathrow Airport" },
            { "code": "FRA", "name": "Frankfurt Airport" }
        ]
    }

    for category, airport_list in airports_data.items():
        for airport in airport_list:
            Airport.objects.get_or_create(
                code=airport["code"],
                defaults={'name': airport["name"]}
            )
    print(f"Seeded {Airport.objects.count()} Airports.")

    # Optional: Seed a few Airlines for Flight testing
    airlines = [
        {"code": "AC", "name": "Air Canada"},
        {"code": "BR", "name": "EVA Air"},
        {"code": "CI", "name": "China Airlines"},
        {"code": "CX", "name": "Cathay Pacific"},
        {"code": "NH", "name": "All Nippon Airways"},
        {"code": "JL", "name": "Japan Airlines"},
    ]
    for al in airlines:
       from apps.flights.models import Airline
       Airline.objects.get_or_create(code=al["code"], defaults={'name': al["name"]})
    print("Seeded Airlines.")

if __name__ == '__main__':
    run()
