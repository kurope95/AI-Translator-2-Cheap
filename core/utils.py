import sys
from pathlib import Path

from core.constants import GEMINI_BACKEND_MODEL_MAP, GEMINI_REQUEST_CHAR_LIMIT, LANGUAGE_CODES


def _is_packaged_app() -> bool:
    return getattr(sys, "frozen", False) or Path(sys.argv[0]).suffix.lower() == ".exe"


def _is_gemini_backend(backend: str) -> bool:
    return backend in GEMINI_BACKEND_MODEL_MAP


def _summarize_numeric_values(values, digits: int = 1) -> dict:
    if not values:
        return {"count": 0, "min": 0, "max": 0, "avg": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values), digits),
    }


def _get_gemini_execution_settings(backend: str) -> dict:
    if backend in ["gemini", "gemini-25-flash", "gemini-37-flash"]:
        return {"max_workers": 16, "request_item_limit": 18}
    if backend in ["gemini-35-flash-lite"]:
        return {"max_workers": 18, "request_item_limit": 18}
    return {"max_workers": 24, "request_item_limit": 20}


def _deepl_api_base(api_key: str) -> str:
    return "https://api-free.deepl.com" if api_key.endswith(":fx") else "https://api.deepl.com"


def _get_base_target_language(target_lang: str) -> str:
    if target_lang in {"Serbian (Latin)", "Serbian (Azbuka)"}:
        return "Serbian"
    return target_lang


def _get_google_target_code(target_lang: str) -> str:
    if target_lang in {"Serbian (Latin)", "Serbian (Azbuka)"}:
        return "sr"
    return LANGUAGE_CODES.get(target_lang, target_lang)
