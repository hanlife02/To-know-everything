from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

SETTINGS_PATH = Path(__file__).resolve().parent / "data" / "llm_settings.json"
MODELS_CACHE_PATH = Path(__file__).resolve().parent / "data" / "llm_models.json"
SUPPORTED_API_FORMATS = {"openai", "claude"}
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"


@dataclass(slots=True)
class LLMSettings:
    api_format: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model: str = ""


def load_llm_settings(path: Path = SETTINGS_PATH) -> LLMSettings:
    settings = LLMSettings(
        api_format=os.getenv("LLM_API_FORMAT", "openai").strip().lower() or "openai",
        base_url=os.getenv("LLM_BASE_URL", "").strip(),
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        model=os.getenv("LLM_MODEL", "").strip(),
    )

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        settings = LLMSettings(
            api_format=str(payload.get("api_format", settings.api_format)).strip().lower() or "openai",
            base_url=str(payload.get("base_url", settings.base_url)).strip(),
            api_key=str(payload.get("api_key", settings.api_key)).strip(),
            model=str(payload.get("model", settings.model)).strip(),
        )

    if settings.api_format not in SUPPORTED_API_FORMATS:
        settings.api_format = "openai"

    return settings


def save_llm_settings(settings: LLMSettings, path: Path = SETTINGS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def serialize_llm_settings(settings: LLMSettings) -> dict[str, str]:
    return asdict(settings)


def mask_secret(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * (len(value) - keep * 2)}{value[-keep:]}"


def get_response_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:300] if text else f"HTTP {response.status_code}"

    for key in ("error", "message", "description"):
        value = payload.get(key)
        if isinstance(value, dict):
            nested = value.get("message") or value.get("type")
            if nested:
                return str(nested)
        elif value:
            return str(value)

    return json.dumps(payload, ensure_ascii=False)


def get_llm_status(settings: LLMSettings) -> dict[str, Any]:
    return {
        "api_format": settings.api_format,
        "base_url_configured": bool(settings.base_url),
        "api_key_configured": bool(settings.api_key),
        "model_selected": bool(settings.model),
        "masked_api_key": mask_secret(settings.api_key),
    }


def normalize_base_url(base_url: str) -> str:
    return base_url.strip().rstrip("/")


def build_models_url(settings: LLMSettings) -> str:
    base_url = normalize_base_url(settings.base_url)
    if not base_url:
        raise ValueError("LLM base URL is not configured.")

    if settings.api_format == "openai":
        if base_url.endswith("/models"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/models"
        return f"{base_url}/v1/models"

    if settings.api_format == "claude":
        if base_url.endswith("/models"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/models"
        return f"{base_url}/v1/models"

    raise ValueError(f"Unsupported API format: {settings.api_format}")


def build_model_headers(settings: LLMSettings) -> dict[str, str]:
    if not settings.api_key:
        raise ValueError("LLM API key is not configured.")

    if settings.api_format == "openai":
        return {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }

    if settings.api_format == "claude":
        return {
            "x-api-key": settings.api_key,
            "anthropic-version": DEFAULT_ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    raise ValueError(f"Unsupported API format: {settings.api_format}")


def build_generation_url(settings: LLMSettings) -> str:
    base_url = normalize_base_url(settings.base_url)
    if not base_url:
        raise ValueError("LLM base URL is not configured.")

    if settings.api_format == "openai":
        if base_url.endswith("/chat/completions"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"

    if settings.api_format == "claude":
        if base_url.endswith("/messages"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/messages"
        return f"{base_url}/v1/messages"

    raise ValueError(f"Unsupported API format: {settings.api_format}")


def build_generation_headers(settings: LLMSettings) -> dict[str, str]:
    return build_model_headers(settings)


def flatten_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            text = item.strip()
            if text:
                parts.append(text)
            continue

        if not isinstance(item, dict):
            continue

        if item.get("type") in {"text", "output_text"}:
            text = item.get("text", "")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
                continue

        nested_text = item.get("content")
        if isinstance(nested_text, str) and nested_text.strip():
            parts.append(nested_text.strip())

    return "\n".join(parts).strip()


def parse_openai_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"Unexpected OpenAI payload: {payload}")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError(f"Unexpected OpenAI payload: {payload}")

    message = first_choice.get("message", {})
    if not isinstance(message, dict):
        raise RuntimeError(f"Unexpected OpenAI payload: {payload}")

    content = flatten_text_content(message.get("content"))
    if not content:
        raise RuntimeError(f"Empty OpenAI response content: {payload}")
    return content


def parse_claude_text(payload: dict[str, Any]) -> str:
    content = flatten_text_content(payload.get("content"))
    if not content:
        raise RuntimeError(f"Empty Claude response content: {payload}")
    return content


def generate_text(
    settings: LLMSettings,
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.4,
    max_output_tokens: int = 1200,
    timeout: int = 60,
) -> str:
    if not settings.model:
        raise ValueError("LLM model is not configured.")

    if settings.api_format == "openai":
        payload = {
            "model": settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
    elif settings.api_format == "claude":
        payload = {
            "model": settings.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
    else:
        raise ValueError(f"Unsupported API format: {settings.api_format}")

    response = requests.post(
        build_generation_url(settings),
        headers=build_generation_headers(settings),
        json=payload,
        timeout=timeout,
    )
    if not response.ok:
        raise RuntimeError(get_response_error_message(response))

    response_payload = response.json()
    if settings.api_format == "openai":
        return parse_openai_text(response_payload)
    return parse_claude_text(response_payload)


def fetch_models(settings: LLMSettings, timeout: int = 30) -> list[dict[str, str]]:
    response = requests.get(
        build_models_url(settings),
        headers=build_model_headers(settings),
        timeout=timeout,
    )
    if not response.ok:
        raise RuntimeError(get_response_error_message(response))

    payload = response.json()
    data = payload.get("data", [])

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected model list payload: {payload}")

    models: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or item.get("name") or "").strip()
        if not model_id:
            continue
        models.append(
            {
                "id": model_id,
                "label": str(item.get("display_name") or model_id).strip(),
            }
        )

    if not models:
        raise RuntimeError("No models were returned by the provider.")

    return models


def save_models_cache(
    models: list[dict[str, str]],
    path: Path = MODELS_CACHE_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"models": models}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_models_cache(path: Path = MODELS_CACHE_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    models = payload.get("models", [])
    return models if isinstance(models, list) else []
