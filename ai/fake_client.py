from ai.schemas import ParsedVehicleData,GeneratedPostContent,GeneratedPlatformContent

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


def fake_generate_post_content(vehicle) -> GeneratedPostContent:
    vehicle_name = f"{vehicle.brand} {vehicle.model}".strip()

    return GeneratedPostContent(
        base_title=f"{vehicle_name} disponível",
        base_caption=(
            f"{vehicle_name} {vehicle.version or ''}\n"
            f"Uma opção interessante para quem busca um carro para o dia a dia.\n"
            f"Entre em contato para mais informações."
        ),
        cta="Chame no WhatsApp para mais informações.",
        hashtags="#carros #bauru #rodoviariaveiculos",
    )
def fake_generate_platform_content(social_post) -> list[GeneratedPlatformContent]:
    vehicle = social_post.vehicle
    vehicle_name = f"{vehicle.brand} {vehicle.model}".strip()

    return [
        GeneratedPlatformContent(
            platform="instagram",
            caption=(
                f"{social_post.base_caption}\n\n"
                f"Disponível na Rodoviária Veículos.\n"
                f"Chame no WhatsApp para mais informações."
            ),
            hashtags="#carros #bauru #rodoviariaveiculos",
        ),
        GeneratedPlatformContent(
            platform="facebook",
            caption=(
                f"{social_post.base_caption}\n\n"
                f"Veículo disponível para visita na loja.\n"
                f"Entre em contato para saber mais."
            ),
            hashtags="#RodoviariaVeiculos #Bauru",
        ),
        GeneratedPlatformContent(
            platform="tiktok",
            caption=(
                f"{vehicle_name} passando na sua tela.\n"
                f"Quer saber mais? Chama a gente."
            ),
            hashtags="#carros #carrosembauru",
        ),
        GeneratedPlatformContent(
            platform="youtube",
            title=f"{vehicle_name} disponível em Bauru",
                   description=(
                f"{social_post.base_caption}\n\n"
                f"Rodoviária Veículos\n"
                f"Av. Nações Unidas 1-50, Bauru\n"
                f"WhatsApp (14) 99711-2299"
            ),
            hashtags="#carros #bauru",
        ),
        GeneratedPlatformContent(
            platform="google_business",
            title=f"{vehicle_name} disponível",
            description=(
                f"{vehicle_name} disponível na Rodoviária Veículos.\n"
                f"Consulte condições e agende sua visita.\n\n"
                f"Av. Nações Unidas 1-50, Bauru\n"
                f"WhatsApp (14) 99711-2299"
            ),
        ),
    ]
