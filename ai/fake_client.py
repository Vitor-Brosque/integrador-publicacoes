from ai.schemas import ParsedVehicleData


def fake_parse_vehicle(raw_input: str) -> ParsedVehicleData:
    raw_lower = raw_input.lower()

    data = ParsedVehicleData()

    if "toyota" in raw_lower:
        data.brand = "Toyota"

    if "etios" in raw_lower:
        data.model = "Etios"

    if "volkswagen" in raw_lower or "vw" in raw_lower:
        data.brand = "Volkswagen"

    if "gol" in raw_lower:
        data.model = "Gol"

    if "hatch" in raw_lower:
        data.category = "hatch"

    if "sedan" in raw_lower:
        data.category = "sedan"

    if "manual" in raw_lower:
        data.transmission = "Manual"

    if "automático" in raw_lower or "automatico" in raw_lower:
        data.transmission = "Automático"

    if "flex" in raw_lower:
        data.fuel = "Flex"

    data.usage_profile = "Veículo indicado para uso diário."
    data.target_audience = "Público que busca praticidade e economia."
    data.commercial_positioning = "Opção interessante para quem procura um veículo funcional."
    data.enrichment_source = "fake_client"

    return data
