from django.db import models

class Flight(models.Model):
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20)
    departure_airport = models.CharField(max_length=3)
    arrival_airport = models.CharField(max_length=3)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    pnr_code = models.CharField(max_length=20, verbose_name="PNR")
    ticket_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.airline} {self.flight_number} ({self.pnr_code})"
