from dataclasses import dataclass


@dataclass
class ParsedVehicleData:
    brand: str = ""
    model: str = ""
    version: str = ""
    manufacture_year: int | None = None
    model_year: int | None = None
    price: str = ""
    mileage: int | None = None
    color: str = ""
    doors: int | None = None
    transmission: str = ""
    fuel: str = ""
    category: str = "unknown"
    usage_profile: str = ""
    target_audience: str = ""
    commercial_positioning: str = ""
    enrichment_source: str = ""

@dataclass
class GeneratedPostContent:
    base_title: str = ""
    base_caption: str = ""
    cta: str = ""
    hashtags: str = ""
