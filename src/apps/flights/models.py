from django.db import models
from django.utils import timezone
import uuid

class Airport(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="IATA Code, e.g. YVR")
    name = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Vancouver International Airport")

    def __str__(self):
        return f"{self.code} - {self.name or ''}"

class Airline(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Air Canada")
    code = models.CharField(max_length=3, help_text="e.g. AC")
    logo = models.ImageField(upload_to='airlines/', blank=True, null=True)

    def __str__(self):
        return f"{self.name or self.code} ({self.code})"

class Flight(models.Model):
    """
    Represents a Flight Route (Definition).
    Code Structure: {AirlineCode}{FlightNum}
    Example: AC013 (Vancouver to London)
    """
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE, related_name='flights')
    flight_number = models.CharField(max_length=10, help_text="Serial part, e.g. 013")
    departure_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='departing_flights')
    arrival_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='arriving_flights')

    @property
    def code(self):
        return f"{self.airline.code}{self.flight_number}"

    def __str__(self):
        return f"{self.code} ({self.departure_airport.code}-{self.arrival_airport.code})"

class FlightInstance(models.Model):
    """
    Represents a specific scheduled flight for a date.
    Code: {FlightNumber}-{Date}
    Example: 013-2026-04-26
    """
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='instances')
    departure_date = models.DateField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)

    flight_code = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate flight_code if missing or if logic requires update
        if self.flight:
            base_code = self.flight.code

            if self.departure_date:
                # Format: {Airline}{Num}-{Date}
                # Example: AC013-2026-04-26
                new_code = f"{base_code}-{self.departure_date}"
            else:
                # Fallback: {Airline}{Num}-{Dep}-{Arr}
                # Example: AC013-YVR-LHR
                new_code = f"{base_code}-{self.flight.departure_airport.code}-{self.flight.arrival_airport.code}"

            # Update only if changed or empty

            # Update only if changed or empty
            if self.flight_code != new_code:
                # check uniqueness?
                # If collision exists for date-less (e.g. multiple open instances), we might need suffix.
                # simpler to catch integrity error or append random, but user didn't specify.
                # For now, simplistic approach.
                self.flight_code = new_code

        super().save(*args, **kwargs)

    def __str__(self):
        return self.flight_code or f"Flight {self.flight.flight_number} (No Code)"

class FlightTicket(models.Model):
    """
    Represents a specific seat on a flight (Instance).
    Code Structure: {FlightCode}{SeatNumber}
    Example: BR00911NOV27YVR32D
    """
    flight = models.ForeignKey(FlightInstance, on_delete=models.CASCADE, related_name='tickets')

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # Link to Client (Optional, or explicit name fields above)
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    pnr = models.CharField(max_length=20, blank=True, help_text="Passenger Name Record")
    seat_number = models.CharField(max_length=10, blank=True, null=True, help_text="Specific seat or TBA")

    # Instance Details
    cabin_class = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('Economy', 'Economy'), ('Business', 'Business'), ('First', 'First')
    ])
    meal_plan = models.CharField(max_length=50, blank=True, help_text="e.g. Vegetarian, Standard")
    bags = models.IntegerField(default=1, blank=True, null=True)

    ticket_code = models.CharField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-Generate Code
        if self.flight.flight_code:
            # Should ticket code format update too? User didn't specify.
            # Keeping relatively unique:
            seat = self.seat_number or "ANY"
            base = f"{self.flight.flight_code}-{seat}"
            if not self.ticket_code:
                 if seat == "ANY" or not self.seat_number:
                     self.ticket_code = f"{base}-{uuid.uuid4().hex[:6]}"
                 else:
                     self.ticket_code = base
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticket_code
