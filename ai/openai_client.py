import json
import os

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - dependency is optional in test env
    OpenAI = None


OPENAI_DEFAULT_MODEL = "gpt-4.1-mini"


def generate_structured_post_with_openai(compact_input: dict) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    if OpenAI is None:
        raise RuntimeError("The openai package is not installed.")

    model = os.getenv("OPENAI_MODEL", OPENAI_DEFAULT_MODEL).strip() or OPENAI_DEFAULT_MODEL
    client = OpenAI(api_key=api_key)

    prompt = _build_prompt(compact_input)
    schema = _build_response_schema(compact_input)

    last_error = None
    for response_format in (
        {"type": "json_schema", "json_schema": schema},
        {"type": "json_object"},
    ):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você gera copy automotiva em pt-BR para posts de veículo. "
                            "Responda apenas com JSON válido."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=response_format,
                temperature=0.3,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise RuntimeError("OpenAI response is not a JSON object.")
            return parsed
        except Exception as exc:  # pragma: no cover - network/API failure path
            last_error = exc

    raise RuntimeError(f"OpenAI structured post generation failed: {last_error}") from last_error


def _build_prompt(compact_input: dict) -> str:
    selected_platforms = compact_input.get("platforms", [])
    compliance_rules = compact_input.get("compliance_rules", [])
    lines = [
        "Gere conteúdo automotivo em JSON.",
        "Use pt-BR.",
        "Use apenas as plataformas selecionadas.",
        "Objetivo: gerar leads qualificados para WhatsApp, simulação, avaliação de usado, visita na loja e venda.",
        "Não invente garantia, laudo, procedência, único dono, revisões, baixa quilometragem, IPVA pago, pneus novos, aprovação de financiamento, valor de parcela ou estado de conservação.",
        "Entrada compacta:",
        json.dumps(compact_input, ensure_ascii=False),
        "Regras de compliance:",
        json.dumps(compliance_rules, ensure_ascii=False),
        "Saída: apenas JSON válido e compacto.",
        f"Plataformas selecionadas: {json.dumps(selected_platforms, ensure_ascii=False)}",
    ]
    return "\n".join(lines)


def _build_response_schema(compact_input: dict) -> dict:
    selected_platforms = [platform for platform in compact_input.get("platforms", []) if platform in _platform_schema_map()]

    platform_properties = {
        platform: _platform_schema_map()[platform] for platform in selected_platforms
    }

    return {
        "name": "vehicle_post_content",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "base_post",
                "platform_posts",
                "carousel_structure",
                "video_structure",
                "compliance_alerts",
            ],
            "properties": {
                "base_post": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["base_title", "base_caption", "cta", "hashtags"],
                    "properties": {
                        "base_title": {"type": "string"},
                        "base_caption": {"type": "string"},
                        "cta": {"type": "string"},
                        "hashtags": {"type": "string"},
                    },
                },
                "platform_posts": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": platform_properties,
                    "required": selected_platforms,
                },
                "carousel_structure": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["enabled", "slides"],
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "slides": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["title", "body"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "video_structure": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["enabled", "hook", "script", "on_screen_text", "caption", "cta"],
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "hook": {"type": "string"},
                        "script": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "on_screen_text": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "caption": {"type": "string"},
                        "cta": {"type": "string"},
                    },
                },
                "compliance_alerts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    }


def _platform_schema_map() -> dict:
    return {
        "instagram": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "caption", "description", "hashtags", "hook", "format_notes"],
            "properties": {
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "string"},
                "hook": {"type": "string"},
                "format_notes": {"type": "string"},
            },
        },
        "facebook": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "caption", "description", "hashtags", "format_notes"],
            "properties": {
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "string"},
                "format_notes": {"type": "string"},
            },
        },
        "tiktok": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "caption",
                "description",
                "hashtags",
                "hook",
                "short_script",
                "on_screen_text",
                "format_notes",
            ],
            "properties": {
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "string"},
                "hook": {"type": "string"},
                "short_script": {"type": "string"},
                "on_screen_text": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "format_notes": {"type": "string"},
            },
        },
        "youtube": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "caption", "description", "hashtags", "hook", "short_script", "format_notes"],
            "properties": {
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "string"},
                "hook": {"type": "string"},
                "short_script": {"type": "string"},
                "format_notes": {"type": "string"},
            },
        },
        "google_business": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "caption", "description", "hashtags", "local_update", "format_notes"],
            "properties": {
                "title": {"type": "string"},
                "caption": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "string"},
                "local_update": {"type": "string"},
                "format_notes": {"type": "string"},
            },
        },
    }
