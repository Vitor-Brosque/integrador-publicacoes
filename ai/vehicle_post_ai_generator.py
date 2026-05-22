import json
import logging
import re
import os
import sys
from copy import deepcopy
from decimal import Decimal

from ai.fake_client import fake_parse_vehicle
from ai.openai_client import generate_structured_post_with_openai


DEFAULT_PLATFORMS = [
    "instagram",
    "facebook",
    "tiktok",
    "youtube",
    "google_business",
]

COMPLIANCE_RULES = [
    "Não inventar garantia",
    "Não inventar laudo cautelar",
    "Não inventar procedência",
    "Não inventar único dono",
    "Não inventar revisões",
    "Não inventar baixa quilometragem",
    "Não inventar IPVA pago",
    "Não inventar pneus novos",
    "Não inventar aprovação de financiamento",
    "Não inventar valor de parcela",
    "Não inventar estado de conservação",
]


logger = logging.getLogger(__name__)


def build_vehicle_post_prompt(vehicle, media_assets, post_type, platforms, compact_input=None):
    compact_input = compact_input or build_compact_ai_input(vehicle, media_assets, post_type, platforms)
    prompt = {
        "task": "Gerar copy automotiva estruturada em JSON.",
        "input": compact_input,
        "expected_output": _empty_structure(compact_input["platforms"], post_type),
    }

    return json.dumps(prompt, ensure_ascii=False, indent=2)


def generate_ai_post_content(vehicle, media_assets, post_type, platforms):
    compact_input = build_compact_ai_input(vehicle, media_assets, post_type, platforms)
    fallback_result = generate_fake_structured_ai_response(
        vehicle,
        media_assets,
        post_type,
        platforms,
        compact_input=compact_input,
    )

    if not _openai_post_ai_enabled():
        return fallback_result

    if not os.getenv("OPENAI_API_KEY", "").strip():
        return fallback_result

    try:
        openai_result = generate_structured_post_with_openai(compact_input)
        normalized_openai_result = normalize_ai_result(
            openai_result,
            selected_platforms=compact_input["platforms"],
            post_type=post_type,
        )
        return _merge_openai_result(fallback_result, normalized_openai_result)
    except Exception as exc:  # pragma: no cover - API/network failure path
        logger.warning("OpenAI post generation failed, using fallback: %s", exc)
        print(f"OpenAI post generation failed, using fallback: {exc}")
        return fallback_result


def normalize_ai_result(result, selected_platforms, post_type):
    normalized = {
        "base_post": _normalize_base_post((result or {}).get("base_post", {})),
        "platform_posts": {},
        "carousel_structure": {
            "enabled": post_type == "carousel",
            "slides": [],
        },
        "video_structure": {
            "enabled": post_type == "video",
            "hook": "",
            "script": [],
            "on_screen_text": [],
            "caption": "",
            "cta": "",
        },
        "compliance_alerts": _normalize_string_list((result or {}).get("compliance_alerts", [])),
    }

    platform_posts = (result or {}).get("platform_posts", {})
    for platform in _normalize_platforms(selected_platforms):
        normalized["platform_posts"][platform] = _normalize_platform_post(
            platform,
            platform_posts.get(platform, {}),
        )

    carousel_structure = (result or {}).get("carousel_structure", {}) or {}
    if post_type == "carousel":
        normalized["carousel_structure"] = {
            "enabled": True,
            "slides": _normalize_carousel_slides(carousel_structure.get("slides", [])),
        }

    video_structure = (result or {}).get("video_structure", {}) or {}
    if post_type == "video":
        normalized["video_structure"] = {
            "enabled": True,
            "hook": _normalize_string(video_structure.get("hook", "")),
            "script": _normalize_string_list(video_structure.get("script", [])),
            "on_screen_text": _normalize_string_list(video_structure.get("on_screen_text", [])),
            "caption": _normalize_string(video_structure.get("caption", "")),
            "cta": _normalize_string(video_structure.get("cta", "")),
        }

    return normalized


def _merge_openai_result(fallback_result, openai_result):
    merged = deepcopy(fallback_result)

    merged["base_post"] = _merge_dict_values(merged.get("base_post", {}), openai_result.get("base_post", {}))

    merged_platform_posts = merged.get("platform_posts", {})
    for platform, platform_content in openai_result.get("platform_posts", {}).items():
        if platform not in merged_platform_posts:
            continue
        merged_platform_posts[platform] = _merge_dict_values(
            merged_platform_posts.get(platform, {}),
            platform_content,
        )
    merged["platform_posts"] = merged_platform_posts

    if openai_result.get("carousel_structure", {}).get("enabled"):
        merged["carousel_structure"] = _merge_dict_values(
            merged.get("carousel_structure", {}),
            openai_result.get("carousel_structure", {}),
        )

    if openai_result.get("video_structure", {}).get("enabled"):
        merged["video_structure"] = _merge_dict_values(
            merged.get("video_structure", {}),
            openai_result.get("video_structure", {}),
        )

    merged["compliance_alerts"] = _merge_string_lists(
        merged.get("compliance_alerts", []),
        openai_result.get("compliance_alerts", []),
    )
    return merged


def _openai_post_ai_enabled():
    return os.getenv("OPENAI_POST_AI_ENABLED", "False") == "True" and not _running_under_test()


def _running_under_test():
    return "test" in sys.argv


def generate_fake_structured_ai_response(vehicle, media_assets, post_type, platforms, compact_input=None):
    selected_media = _normalize_media_assets(vehicle, media_assets)
    selected_platforms = _normalize_platforms(platforms)
    parsed_vehicle = fake_parse_vehicle(vehicle.raw_input or "")

    brand = _coalesce_text(
        getattr(vehicle, "brand", ""),
        parsed_vehicle.brand,
        _extract_brand_from_raw(vehicle.raw_input or ""),
    )
    model = _coalesce_text(
        getattr(vehicle, "model", ""),
        parsed_vehicle.model,
        _extract_model_from_raw(vehicle.raw_input or ""),
    )
    version = _coalesce_text(
        getattr(vehicle, "version", ""),
        _extract_version_from_raw(vehicle.raw_input or ""),
    )
    year_model = _coalesce_text(
        _format_year_model(getattr(vehicle, "manufacture_year", None), getattr(vehicle, "model_year", None)),
        _extract_year_model_from_raw(vehicle.raw_input or ""),
    )
    engine = _coalesce_text(
        _extract_engine_from_raw(vehicle.raw_input or "", version),
    )
    transmission = _coalesce_text(
        getattr(vehicle, "transmission", ""),
        parsed_vehicle.transmission,
        _extract_transmission_from_raw(vehicle.raw_input or ""),
    )
    fuel = _coalesce_text(
        getattr(vehicle, "fuel", ""),
        parsed_vehicle.fuel,
        _extract_fuel_from_raw(vehicle.raw_input or ""),
    )
    body_type = _coalesce_text(
        _clean_unknown(getattr(vehicle, "category", "")),
        parsed_vehicle.category,
        _extract_body_type_from_raw(vehicle.raw_input or ""),
    )
    price = _coalesce_text(
        _format_price(getattr(vehicle, "price", None)),
        _extract_price_from_raw(vehicle.raw_input or ""),
    )

    confirmed_facts = _build_confirmed_facts(
        brand=brand,
        model=model,
        version=version,
        year_model=year_model,
        engine=engine,
        transmission=transmission,
        fuel=fuel,
        body_type=body_type,
        price=price,
        media_count=len(selected_media),
    )

    unconfirmed_information = _build_unconfirmed_information(vehicle)
    commercial_inferences = _build_commercial_inferences(
        brand=brand,
        model=model,
        body_type=body_type,
        price=price,
        media_count=len(selected_media),
        post_type=post_type,
    )
    technical_translation = _build_technical_translation(
        brand=brand,
        model=model,
        version=version,
        year_model=year_model,
        transmission=transmission,
        fuel=fuel,
        engine=engine,
    )

    likely_buyer_profile = _build_likely_buyer_profile(body_type, price)
    main_pain = _build_main_pain(body_type, price)
    main_desire = _build_main_desire(body_type)
    likely_objections = _build_likely_objections(vehicle)
    main_commercial_angle = _build_main_commercial_angle(
        brand=brand,
        model=model,
        body_type=body_type,
        price=price,
    )
    best_cta = _build_best_cta(post_type)
    compliance_alerts = _build_compliance_alerts(vehicle, selected_media)

    base_post = _build_base_post(
        brand=brand,
        model=model,
        version=version,
        year_model=year_model,
        price=price,
        body_type=body_type,
        cta=best_cta,
        post_type=post_type,
        media_count=len(selected_media),
    )

    platform_posts = {}
    for platform in selected_platforms:
        platform_posts[platform] = _build_platform_post(
            platform=platform,
            base_post=base_post,
            vehicle_analysis={
                "brand": brand,
                "model": model,
                "version": version,
                "year_model": year_model,
                "engine": engine,
                "transmission": transmission,
                "fuel": fuel,
                "body_type": body_type,
                "price": price,
            },
            post_type=post_type,
            selected_media=selected_media,
            likely_buyer_profile=likely_buyer_profile,
            main_commercial_angle=main_commercial_angle,
            best_cta=best_cta,
        )

    carousel_structure = {
        "enabled": post_type == "carousel",
        "slides": _build_carousel_slides(
            brand=brand,
            model=model,
            version=version,
            year_model=year_model,
            price=price,
            body_type=body_type,
            likely_buyer_profile=likely_buyer_profile,
            main_commercial_angle=main_commercial_angle,
        ) if post_type == "carousel" else [],
    }

    video_structure = {
        "enabled": post_type == "video",
        "hook": "",
        "script": [],
        "on_screen_text": [],
        "caption": "",
        "cta": "",
    }
    if post_type == "video":
        video_structure = _build_video_structure(
            brand=brand,
            model=model,
            version=version,
            year_model=year_model,
            price=price,
            body_type=body_type,
            likely_buyer_profile=likely_buyer_profile,
            best_cta=best_cta,
        )

    return {
        "vehicle_analysis": {
            "brand": brand,
            "model": model,
            "version": version,
            "year_model": year_model,
            "engine": engine,
            "transmission": transmission,
            "fuel": fuel,
            "body_type": body_type,
            "price": price,
            "confirmed_facts": confirmed_facts,
            "unconfirmed_information": unconfirmed_information,
            "commercial_inferences": commercial_inferences,
            "technical_translation": technical_translation,
            "likely_buyer_profile": likely_buyer_profile,
            "main_pain": main_pain,
            "main_desire": main_desire,
            "likely_objections": likely_objections,
            "main_commercial_angle": main_commercial_angle,
            "best_cta": best_cta,
            "compliance_alerts": compliance_alerts,
        },
        "base_post": base_post,
        "platform_posts": platform_posts,
        "carousel_structure": carousel_structure,
        "video_structure": video_structure,
    }


def build_compact_ai_input(vehicle, media_assets, post_type, platforms):
    selected_media = _normalize_media_assets(vehicle, media_assets)
    compact_media = []
    has_video = False
    has_images = False

    for media_item in selected_media:
        media_asset = _resolve_media_asset(media_item)
        media_type = getattr(media_asset, "media_type", "") or ""
        compact_media.append(media_type)
        if media_type == "video":
            has_video = True
        if media_type == "image":
            has_images = True

    return {
        "vehicle_raw_input": vehicle.raw_input,
        "post_type": post_type,
        "platforms": _normalize_platforms(platforms),
        "media": {
            "count": len(selected_media),
            "types": compact_media,
            "has_video": has_video,
            "has_images": has_images,
        },
        "business_goal": "Gerar leads qualificados para WhatsApp, simulação, avaliação de usado e visita na loja.",
        "compliance_rules": COMPLIANCE_RULES,
    }


def _empty_structure(platforms, post_type):
    selected_platforms = _normalize_platforms(platforms)

    platform_posts = {platform: _empty_platform_post(platform) for platform in selected_platforms}

    return {
        "vehicle_analysis": {
            "brand": "",
            "model": "",
            "version": "",
            "year_model": "",
            "engine": "",
            "transmission": "",
            "fuel": "",
            "body_type": "",
            "price": "",
            "confirmed_facts": [],
            "unconfirmed_information": [],
            "commercial_inferences": [],
            "technical_translation": [],
            "likely_buyer_profile": "",
            "main_pain": "",
            "main_desire": "",
            "likely_objections": [],
            "main_commercial_angle": "",
            "best_cta": "",
            "compliance_alerts": [],
        },
        "base_post": {
            "base_title": "",
            "base_caption": "",
            "cta": "",
            "hashtags": "",
        },
        "platform_posts": platform_posts,
        "carousel_structure": {
            "enabled": post_type == "carousel",
            "slides": [],
        },
        "video_structure": {
            "enabled": post_type == "video",
            "hook": "",
            "script": [],
            "on_screen_text": [],
            "caption": "",
            "cta": "",
        },
    }


def _normalize_media_assets(vehicle, media_assets):
    if media_assets is None:
        return list(vehicle.media_assets.order_by("id"))

    return list(media_assets)


def _resolve_media_asset(media_item):
    return getattr(media_item, "media_asset", media_item)


def _normalize_platforms(platforms):
    selected_platforms = platforms or DEFAULT_PLATFORMS
    normalized = []

    for platform in selected_platforms:
        if platform not in normalized:
            normalized.append(platform)

    return normalized


def _coalesce_text(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value not in ("", []):
            return str(value).strip()
    return ""


def _clean_unknown(value):
    if value in (None, "", "unknown"):
        return ""
    return value


def _format_price(value):
    if value in (None, ""):
        return ""

    if isinstance(value, Decimal):
        normalized = f"{value:,.2f}"
        normalized = normalized.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {normalized}"

    return str(value).strip()


def _format_year_model(manufacture_year, model_year):
    if manufacture_year and model_year:
        return f"{manufacture_year}/{model_year}"
    if model_year:
        return str(model_year)
    if manufacture_year:
        return str(manufacture_year)
    return ""


def _extract_price_from_raw(raw_input):
    match = re.search(r"R\$\s*([0-9\.\,]+)", raw_input or "", re.IGNORECASE)
    if not match:
        return ""
    return f"R$ {match.group(1)}"


def _extract_year_model_from_raw(raw_input):
    match = re.search(r"(\d{4})\s*[/\-]\s*(\d{4})", raw_input or "")
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    match = re.search(r"\b(19|20)\d{2}\b", raw_input or "")
    if match:
        return match.group(0)
    return ""


def _extract_version_from_raw(raw_input):
    lines = [line.strip() for line in (raw_input or "").splitlines() if line.strip()]
    if len(lines) > 1:
        second_line = lines[1]
        if not re.search(r"R\$", second_line, re.IGNORECASE) and not re.search(r"\d{4}\s*[/\-]\s*\d{4}", second_line):
            return second_line
    return ""


def _extract_engine_from_raw(raw_input, version):
    candidate = version or raw_input or ""
    match = re.search(r"\b\d(?:[.,]\d+)?\b", candidate)
    if match:
        return match.group(0).replace(",", ".")
    return ""


def _extract_transmission_from_raw(raw_input):
    raw_lower = (raw_input or "").lower()
    if "automático" in raw_lower or "automatico" in raw_lower:
        return "Automático"
    if "manual" in raw_lower:
        return "Manual"
    return ""


def _extract_fuel_from_raw(raw_input):
    raw_lower = (raw_input or "").lower()
    if "flex" in raw_lower:
        return "Flex"
    if "gasolina" in raw_lower:
        return "Gasolina"
    if "etanol" in raw_lower:
        return "Etanol"
    if "diesel" in raw_lower:
        return "Diesel"
    return ""


def _extract_body_type_from_raw(raw_input):
    raw_lower = (raw_input or "").lower()
    if "hatch" in raw_lower:
        return "hatch"
    if "sedan" in raw_lower:
        return "sedan"
    if "suv" in raw_lower:
        return "suv"
    if "picape" in raw_lower or "pickup" in raw_lower:
        return "pickup"
    return ""


def _extract_brand_from_raw(raw_input):
    raw_lower = (raw_input or "").lower()
    known_brands = [
        "volkswagen",
        "toyota",
        "chevrolet",
        "fiat",
        "ford",
        "honda",
        "hyundai",
        "jeep",
        "renault",
        "nissan",
        "peugeot",
        "citroen",
        "citroën",
        "kia",
        "bmw",
        "mercedes",
        "audi",
    ]
    for brand in known_brands:
        if brand in raw_lower:
            return brand.title().replace("Volkswagen", "Volkswagen").replace("Bmw", "BMW")
    return ""


def _extract_model_from_raw(raw_input):
    lines = [line.strip() for line in (raw_input or "").splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        tokens = first_line.split()
        if len(tokens) > 1:
            return tokens[1]
    return ""


def _build_confirmed_facts(
    brand,
    model,
    version,
    year_model,
    engine,
    transmission,
    fuel,
    body_type,
    price,
    media_count,
):
    facts = []
    vehicle_name = " ".join(part for part in [brand, model] if part).strip()
    if vehicle_name:
        facts.append(f"Veículo identificado como {vehicle_name}.")
    if version:
        facts.append(f"Versão informada: {version}.")
    if year_model:
        facts.append(f"Ano/modelo informado: {year_model}.")
    if engine:
        facts.append(f"Motorização informada: {engine}.")
    if transmission:
        facts.append(f"Câmbio informado: {transmission}.")
    if fuel:
        facts.append(f"Combustível informado: {fuel}.")
    if body_type:
        facts.append(f"Categoria informada: {body_type}.")
    if price:
        facts.append(f"Preço informado: {price}.")
    facts.append(f"{media_count} mídia(s) selecionada(s) para o post.")
    return facts


def _build_unconfirmed_information(vehicle):
    unconfirmed = []
    checks = [
        ("mileage", "Quilometragem não confirmada."),
        ("color", "Cor não confirmada."),
        ("doors", "Quantidade de portas não confirmada."),
        ("page_id", None),
    ]
    for field_name, message in checks:
        if getattr(vehicle, field_name, None) in (None, "", 0):
            if message:
                unconfirmed.append(message)
    if not getattr(vehicle, "brand", ""):
        unconfirmed.append("Marca não confirmada no cadastro estruturado.")
    if not getattr(vehicle, "model", ""):
        unconfirmed.append("Modelo não confirmado no cadastro estruturado.")
    return unconfirmed


def _build_commercial_inferences(brand, model, body_type, price, media_count, post_type):
    vehicle_name = " ".join(part for part in [brand, model] if part).strip() or "o veículo"
    inferences = [
        f"{vehicle_name} pode atender bem quem busca um carro para uso diário.",
        "A comunicação pode reforçar praticidade, contato rápido e agendamento de visita.",
    ]
    if body_type == "hatch":
        inferences.append("Perfil com apelo para uso urbano e facilidade de manobra.")
    if price:
        inferences.append("O preço pode ser usado como âncora comercial para gerar contato.")
    if media_count > 1 and post_type == "carousel":
        inferences.append("O carrossel ajuda a conduzir a leitura por detalhes e ângulos do veículo.")
    return inferences


def _build_technical_translation(brand, model, version, year_model, transmission, fuel, engine):
    translations = []
    vehicle_name = " ".join(part for part in [brand, model] if part).strip()
    if vehicle_name:
        translations.append(f"{vehicle_name}: nome comercial do veículo.")
    if engine:
        translations.append(f"Motor {engine}: informação técnica de motorização.")
    if transmission:
        translations.append(f"Câmbio {transmission}: forma de troca de marchas.")
    if fuel:
        translations.append(f"Combustível {fuel}: tipo de abastecimento informado.")
    if year_model:
        translations.append(f"Ano/modelo {year_model}: referência de fabricação e comercialização.")
    if version:
        translations.append(f"Versão {version}: pacote de configuração informado.")
    return translations


def _build_likely_buyer_profile(body_type, price):
    if body_type == "hatch":
        return "Pessoa que busca praticidade, uso urbano e custo-benefício."
    if body_type == "sedan":
        return "Pessoa ou família que busca conforto e porta-malas mais amplo."
    if body_type == "suv":
        return "Comprador que busca posição de dirigir elevada e versatilidade."
    if price:
        return "Comprador que compara opções por custo-benefício e facilidade de contato."
    return "Comprador que busca uma opção prática e objetiva."


def _build_main_pain(body_type, price):
    if body_type == "hatch":
        return "Encontrar um carro prático para a rotina sem complicar o uso diário."
    if price:
        return "Encontrar uma opção com preço compatível com o orçamento."
    return "Encontrar um veículo alinhado à necessidade real de uso."


def _build_main_desire(body_type):
    if body_type == "hatch":
        return "Ter agilidade, economia e facilidade para circular na cidade."
    return "Ter um carro que resolva a rotina com segurança e conveniência."


def _build_likely_objections(vehicle):
    objections = ["Quer confirmar detalhes antes de visitar a loja."]
    if not getattr(vehicle, "mileage", None):
        objections.append("Quer confirmar a quilometragem informada.")
    if not getattr(vehicle, "color", ""):
        objections.append("Quer confirmar a cor e o estado visual.")
    return objections


def _build_main_commercial_angle(brand, model, body_type, price):
    vehicle_name = " ".join(part for part in [brand, model] if part).strip() or "o veículo"
    if body_type == "hatch":
        return f"Apresentar {vehicle_name} como uma opção prática e urbana com apelo de custo-benefício."
    if price:
        return f"Usar o preço como ponto de atenção para gerar contato sobre {vehicle_name}."
    return f"Apresentar {vehicle_name} como uma opção objetiva para o cliente entender rapidamente o valor."


def _build_best_cta(post_type):
    if post_type == "video":
        return "Chame no WhatsApp para tirar dúvidas e agendar uma visita."
    if post_type == "carousel":
        return "Veja os detalhes nas imagens e chame no WhatsApp para simulação."
    return "Chame no WhatsApp para receber mais detalhes e agendar sua visita."


def _build_compliance_alerts(vehicle, selected_media):
    alerts = [
        "Não afirmar garantia, laudo, procedência ou revisões sem confirmação documental.",
        "Não prometer condições de financiamento, parcela ou aprovação sem validação comercial.",
    ]
    if len(selected_media) == 0:
        alerts.append("Nenhuma mídia selecionada para validação do post.")
    if getattr(vehicle, "mileage", None) in (None, ""):
        alerts.append("Quilometragem não confirmada: evitar mencionar baixa quilometragem.")
    if getattr(vehicle, "price", None) in (None, ""):
        alerts.append("Preço não confirmado: evitar criar chamada com valor.")
    return alerts


def _build_base_post(brand, model, version, year_model, price, body_type, cta, post_type, media_count):
    vehicle_name = " ".join(part for part in [brand, model] if part).strip()
    title_parts = [vehicle_name, version, year_model]
    base_title = " - ".join(part for part in title_parts if part).strip()
    if not base_title:
        base_title = "Veículo disponível"

    intro = [
        base_title,
        "Conteúdo estruturado para gerar interesse real e contato qualificado.",
    ]
    if price:
        intro.append(f"Preço informado: {price}.")
    if body_type:
        intro.append(f"Categoria: {body_type}.")

    if post_type == "carousel":
        intro.append("Confira os detalhes nas imagens.")
    elif post_type == "video":
        intro.append("Assista ao vídeo para entender os principais pontos do veículo.")
    else:
        intro.append("Post pensado para leitura rápida em imagem única.")

    intro.append(f"{media_count} mídia(s) vinculada(s) ao post.")

    hashtags = _build_hashtags(brand, model, body_type)

    return {
        "base_title": base_title,
        "base_caption": "\n".join(intro),
        "cta": cta,
        "hashtags": hashtags,
    }


def _build_hashtags(brand, model, body_type):
    candidates = [
        "#carros",
        "#seminovos",
        "#carrosusados",
        "#rodoviariaveiculos",
    ]
    if brand:
        candidates.append(f"#{brand.replace(' ', '')}".lower())
    if model:
        candidates.append(f"#{model.replace(' ', '')}".lower())
    if body_type:
        candidates.append(f"#{body_type}".lower())
    return " ".join(dict.fromkeys(candidates))


def _build_platform_post(
    platform,
    base_post,
    vehicle_analysis,
    post_type,
    selected_media,
    likely_buyer_profile,
    main_commercial_angle,
    best_cta,
):
    vehicle_name = " ".join(
        part for part in [vehicle_analysis["brand"], vehicle_analysis["model"]] if part
    ).strip() or "o veículo"

    if platform == "instagram":
        return {
            "title": base_post["base_title"],
            "caption": "\n".join(
                part for part in [
                    base_post["base_caption"],
                    base_post["cta"],
                ] if part
            ),
            "description": (
                f"{vehicle_name} em destaque para quem busca contato rápido, "
                f"leitura clara e foco em conversão."
            ),
            "hashtags": base_post["hashtags"],
            "format_notes": "Legenda objetiva, foco visual e CTA no final.",
        }

    if platform == "facebook":
        return {
            "title": f"{vehicle_name} disponível",
            "caption": "\n".join(
                part for part in [
                    f"{vehicle_name} disponível para quem busca uma opção clara e objetiva.",
                    base_post["cta"],
                ] if part
            ),
            "description": (
                f"{base_post['base_caption']}\n\n"
                f"Perfil indicado: {likely_buyer_profile}"
            ),
            "hashtags": base_post["hashtags"],
            "format_notes": "Texto mais explicativo, com foco em contexto e visita na loja.",
        }

    if platform == "tiktok":
        hook = f"Olha esse {vehicle_name}."
        if post_type == "video":
            short_script = (
                f"Gancho: {hook}\n"
                f"Mostre os pontos fortes sem prometer o que não foi confirmado.\n"
                f"Feche com CTA para WhatsApp."
            )
        else:
            short_script = (
                f"Mostre {vehicle_name} em destaque.\n"
                f"Foque em {main_commercial_angle.lower()}.\n"
                f"Chame para contato rápido."
            )
        return {
            "title": hook,
            "caption": f"{base_post['base_caption']}\n\n{base_post['cta']}",
            "description": short_script,
            "hashtags": base_post["hashtags"],
            "hook": hook,
            "short_script": short_script,
            "on_screen_text": [
                vehicle_name,
                vehicle_analysis["year_model"] or "Ano/modelo sob consulta",
                best_cta,
            ],
            "format_notes": "Linguagem rápida, visual direto e ritmo de retenção.",
        }

    if platform == "youtube":
        return {
            "title": f"{vehicle_name} em destaque",
            "caption": base_post["base_caption"],
            "description": "\n".join(
                part for part in [
                    base_post["base_caption"],
                    f"Resumo comercial: {main_commercial_angle}",
                    f"CTA: {best_cta}",
                ] if part
            ),
            "hashtags": base_post["hashtags"],
            "hook": f"Veja os detalhes deste {vehicle_name}.",
            "short_script": (
                f"Apresentar {vehicle_name}, destacar pontos confirmados, "
                f"e chamar para WhatsApp ao final."
            ),
            "format_notes": "Título claro, descrição informativa e CTA explícito.",
        }

    if platform == "google_business":
        return {
            "title": f"{vehicle_name} disponível na loja",
            "caption": base_post["base_caption"],
            "description": "\n".join(
                part for part in [
                    f"{vehicle_name} disponível para visita.",
                    f"Perfil indicado: {likely_buyer_profile}",
                    best_cta,
                ] if part
            ),
            "hashtags": base_post["hashtags"],
            "local_update": "Atualização local para visita, contato e simulação.",
            "format_notes": "Mensagem curta, objetiva e com apelo local.",
        }

    return _empty_platform_post(platform)


def _empty_platform_post(platform):
    payload = {
        "title": "",
        "caption": "",
        "description": "",
        "hashtags": "",
        "format_notes": "",
    }
    if platform == "tiktok":
        payload.update(
            {
                "hook": "",
                "short_script": "",
                "on_screen_text": [],
            }
        )
    if platform == "youtube":
        payload.update(
            {
                "hook": "",
                "short_script": "",
            }
        )
    if platform == "google_business":
        payload.update({"local_update": ""})
    return payload


def _normalize_base_post(base_post):
    base_post = base_post or {}
    return {
        "base_title": _normalize_string(base_post.get("base_title", "")),
        "base_caption": _normalize_string(base_post.get("base_caption", "")),
        "cta": _normalize_string(base_post.get("cta", "")),
        "hashtags": _normalize_string(base_post.get("hashtags", "")),
    }


def _normalize_platform_post(platform, platform_post):
    platform_post = platform_post or {}
    normalized = {
        "title": _normalize_string(platform_post.get("title", "")),
        "caption": _normalize_string(platform_post.get("caption", "")),
        "description": _normalize_string(platform_post.get("description", "")),
        "hashtags": _normalize_string(platform_post.get("hashtags", "")),
        "format_notes": _normalize_string(platform_post.get("format_notes", "")),
    }
    if platform == "instagram":
        normalized["hook"] = _normalize_string(platform_post.get("hook", ""))
    if platform == "tiktok":
        normalized["hook"] = _normalize_string(platform_post.get("hook", ""))
        normalized["short_script"] = _normalize_string(platform_post.get("short_script", ""))
        normalized["on_screen_text"] = _normalize_string_list(platform_post.get("on_screen_text", []))
    if platform == "youtube":
        normalized["hook"] = _normalize_string(platform_post.get("hook", ""))
        normalized["short_script"] = _normalize_string(platform_post.get("short_script", ""))
    if platform == "google_business":
        normalized["local_update"] = _normalize_string(platform_post.get("local_update", ""))
    return normalized


def _normalize_carousel_slides(slides):
    normalized_slides = []
    for slide in slides or []:
        if not isinstance(slide, dict):
            continue
        normalized_slides.append(
            {
                "title": _normalize_string(slide.get("title", "")),
                "body": _normalize_string(slide.get("body", slide.get("copy", ""))),
            }
        )
    return normalized_slides


def _normalize_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_string_list(values):
    normalized = []
    for value in values or []:
        text = _normalize_string(value)
        if text:
            normalized.append(text)
    return normalized


def _merge_dict_values(base_dict, override_dict):
    merged = deepcopy(base_dict or {})
    for key, value in (override_dict or {}).items():
        if isinstance(value, list):
            normalized_list = _normalize_string_list(value)
            if normalized_list:
                merged[key] = normalized_list
            elif key not in merged:
                merged[key] = []
            continue
        if isinstance(value, dict):
            merged[key] = _merge_dict_values(merged.get(key, {}), value)
            continue
        if isinstance(value, bool):
            merged[key] = value
            continue

        text = _normalize_string(value)
        if text:
            merged[key] = text
        elif key not in merged:
            merged[key] = ""
    return merged


def _merge_string_lists(base_values, override_values):
    merged = []
    for value in (base_values or []) + (override_values or []):
        text = _normalize_string(value)
        if text and text not in merged:
            merged.append(text)
    return merged


def _build_carousel_slides(
    brand,
    model,
    version,
    year_model,
    price,
    body_type,
    likely_buyer_profile,
    main_commercial_angle,
):
    vehicle_name = " ".join(part for part in [brand, model] if part).strip() or "o veículo"
    return [
        {
            "slide": 1,
            "title": f"{vehicle_name} em destaque",
            "copy": f"{version or 'Versão informada no cadastro'}",
            "visual_hint": "Foto de abertura com o veículo em plano principal.",
        },
        {
            "slide": 2,
            "title": "Resumo técnico",
            "copy": f"{year_model or 'Ano/modelo sob consulta'} | {body_type or 'Categoria sob consulta'}",
            "visual_hint": "Detalhes técnicos e imagem de apoio.",
        },
        {
            "slide": 3,
            "title": "Ponto comercial",
            "copy": main_commercial_angle,
            "visual_hint": "Texto curto com destaque do benefício principal.",
        },
        {
            "slide": 4,
            "title": "Perfil ideal",
            "copy": likely_buyer_profile,
            "visual_hint": "Imagem contextual para identificação do público.",
        },
        {
            "slide": 5,
            "title": "Chamada final",
            "copy": f"Converse no WhatsApp para saber mais sobre {price or 'condições comerciais'}.",
            "visual_hint": "Encerramento com CTA forte.",
        },
    ]


def _build_video_structure(brand, model, version, year_model, price, body_type, likely_buyer_profile, best_cta):
    vehicle_name = " ".join(part for part in [brand, model] if part).strip() or "o veículo"
    hook = f"Olha esse {vehicle_name}."
    script = [
        f"Apresentar {vehicle_name} com foco nos pontos confirmados.",
        f"Explicar {version or 'a versão e os detalhes do cadastro'} em linguagem simples.",
        f"Destacar {year_model or 'ano/modelo sob consulta'} e o apelo comercial.",
        f"Fechar com {best_cta}",
    ]
    on_screen_text = [
        vehicle_name,
        year_model or "Ano/modelo sob consulta",
        price or "Preço sob consulta",
        body_type or "Categoria sob consulta",
    ]
    return {
        "enabled": True,
        "hook": hook,
        "script": script,
        "on_screen_text": on_screen_text,
        "caption": (
            f"{vehicle_name} pensado para {likely_buyer_profile.lower()}.\n"
            f"{best_cta}"
        ),
        "cta": best_cta,
    }
