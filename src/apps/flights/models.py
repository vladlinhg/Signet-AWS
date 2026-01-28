from django.db import models
from django.utils import timezone

class Flight(models.Model):
    """
    Represents a specific scheduled flight (Trip).
    Code Structure: {Airline+FlightNum}{Date DDMMMYY}{DeptAirport}
    Example: BR00911NOV27YVR
    """
    airline_code = models.CharField(max_length=3, help_text="e.g. AC, BR")
    flight_number = models.CharField(max_length=4, help_text="e.g. 009")
    departure_date = models.DateField()
    departure_airport = models.CharField(max_length=3, help_text="e.g. YVR, YYZ")
    arrival_airport = models.CharField(max_length=3, help_text="e.g. TPE, NRT")

    # Metadata
    airline_name = models.CharField(max_length=100, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)

    code = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-Generate Code
        # Format: {Airline}{FlightNum}{Date DDMMMYY}{DeptAirport}
        if self.airline_code and self.flight_number and self.departure_date and self.departure_airport:
            date_str = self.departure_date.strftime('%d%b%y').upper()
            self.code = f"{self.airline_code}{self.flight_number}{date_str}{self.departure_airport}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.departure_airport}-{self.arrival_airport})"

class FlightTicket(models.Model):
    """
    Represents a specific seat on a flight (Instance).
    Code Structure: {FlightCode}{SeatNumber}
    Example: BR00911NOV27YVR32D
    """
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='tickets')

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
