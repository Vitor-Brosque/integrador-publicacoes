from django.db import models


class VehicleCategory(models.TextChoices):
    HATCH = "hatch", "Hatch"
    SEDAN = "sedan", "Sedan"
    SUV = "suv", "SUV"
    PICKUP = "pickup", "Picape"
    UNKNOWN = "unknown", "Não identificado"


class Vehicle(models.Model):
    raw_input = models.TextField()

    brand = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=120, blank=True)
    version = models.CharField(max_length=160, blank=True)

    model_year = models.PositiveIntegerField(blank=True, null=True)
    manufacture_year = models.PositiveIntegerField(blank=True, null=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    mileage = models.PositiveIntegerField(blank=True, null=True)
    color = models.CharField(max_length=60, blank=True)
    doors = models.PositiveIntegerField(blank=True, null=True)

    transmission = models.CharField(max_length=80, blank=True)
    fuel = models.CharField(max_length=80, blank=True)

    category = models.CharField(
        max_length=30,
        choices=VehicleCategory.choices,
        default=VehicleCategory.UNKNOWN,
    )

    usage_profile = models.TextField(blank=True)
    target_audience = models.TextField(blank=True)
    commercial_positioning = models.TextField(blank=True)
    enrichment_source = models.TextField(blank=True)

    normalized_by_ai = models.BooleanField(default=False)
    enrichment_status = models.CharField(max_length=40, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"

    def __str__(self):
        name = f"{self.brand} {self.model} {self.version}".strip()

        if name:
            return name

        return f"Veículo #{self.id}"
