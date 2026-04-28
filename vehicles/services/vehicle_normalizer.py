from ai.vehicle_parser import parse_vehicle
from vehicles.models import Vehicle


def normalize_vehicle(vehicle: Vehicle):
    parsed_data = parse_vehicle(vehicle.raw_input)

    vehicle.brand = parsed_data.brand
    vehicle.model = parsed_data.model
    vehicle.version = parsed_data.version
    vehicle.manufacture_year = parsed_data.manufacture_year
    vehicle.model_year = parsed_data.model_year
    vehicle.mileage = parsed_data.mileage
    vehicle.color = parsed_data.color
    vehicle.doors = parsed_data.doors
    vehicle.transmission = parsed_data.transmission
    vehicle.fuel = parsed_data.fuel
    vehicle.category = parsed_data.category

    vehicle.usage_profile = parsed_data.usage_profile
    vehicle.target_audience = parsed_data.target_audience
    vehicle.commercial_positioning = parsed_data.commercial_positioning
    vehicle.enrichment_source = parsed_data.enrichment_source

    vehicle.normalized_by_ai = True
    vehicle.enrichment_status = "basic"

    vehicle.save()

    return vehicle
