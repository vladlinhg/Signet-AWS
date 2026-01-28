from django.db import models
from django.utils import timezone

class Airport(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="IATA Code, e.g. YVR")
    name = models.CharField(max_length=100, help_text="e.g. Vancouver International Airport")

    def __str__(self):
        return f"{self.code} - {self.name}"

class Airline(models.Model):
    name = models.CharField(max_length=100, help_text="e.g. Air Canada")
    code = models.CharField(max_length=3, help_text="e.g. AC")
    logo = models.ImageField(upload_to='airlines/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

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

    # Metadata
    airline_name = models.CharField(max_length=100, blank=True, help_text="Legacy/Override name")

    @property
    def code(self):
        return f"{self.airline.code}{self.flight_number}"

    def __str__(self):
        return f"{self.code} ({self.departure_airport.code}-{self.arrival_airport.code})"

class FlightInstance(models.Model):
    """
    Represents a specific scheduled flight for a date.
    Code: {FlightCode}{Date}
    Example: AC01326APR10
    """
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='instances')
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_time = models.TimeField()

    unique_code = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if self.flight and self.departure_date:
            date_str = self.departure_date.strftime('%y%b%d').upper()
            self.unique_code = f"{self.flight.code}{date_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.unique_code}"

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
    seat_number = models.CharField(max_length=10, default="TBA", help_text="Specific seat or TBA")

    # Instance Details
    cabin_class = models.CharField(max_length=20, default='Economy', choices=[
        ('Economy', 'Economy'), ('Business', 'Business'), ('First', 'First')
    ])
    meal_plan = models.CharField(max_length=50, blank=True, help_text="e.g. Vegetarian, Standard")
    bags = models.IntegerField(default=1)

    ticket_code = models.CharField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-Generate Code
        if self.flight.code:
            base = f"{self.flight.code}-{self.seat_number}"
            if self.seat_number == "TBA":
                # Ensure uniqueness for TBA tickets
                import uuid
                self.ticket_code = f"{base}-{uuid.uuid4().hex[:6]}"
            else:
                self.ticket_code = base
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticket_code
