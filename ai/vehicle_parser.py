from ai.fake_client import fake_parse_vehicle
from ai.schemas import ParsedVehicleData


def parse_vehicle(raw_input: str) -> ParsedVehicleData:
    return fake_parse_vehicle(raw_input)
