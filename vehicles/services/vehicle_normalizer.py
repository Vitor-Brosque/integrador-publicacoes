from vehicles.models import Vehicle


def normalize_vehicle(vehicle: Vehicle):
    raw = vehicle.raw_input.lower()

    if "toyota" in raw:
        vehicle.brand = "Toyota"

    if "etios" in raw:
        vehicle.model = "Etios"

    if "hatch" in raw:
        vehicle.category = "hatch"

    if "manual" in raw:
        vehicle.transmission = "Manual"

    if "flex" in raw:
        vehicle.fuel = "Flex"

    vehicle.normalized_by_ai = True
    vehicle.enrichment_status = "basic"

    vehicle.save()

    return vehicle
