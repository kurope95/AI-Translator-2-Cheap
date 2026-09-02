import copy
import json
import os
import sys
import threading
from pathlib import Path

APP_NAME = "AI Translator 2"

_lock = threading.RLock()
_cache: dict | None = None
_cache_mtime: float | None = None


def _is_packaged_app() -> bool:
    return getattr(sys, "frozen", False) or Path(sys.argv[0]).suffix.lower() == ".exe"


def _data_dir() -> Path:
    if _is_packaged_app():
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        data_dir = local_appdata / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).parent.parent


def _config_path() -> Path:
    return _data_dir() / "config.json"


def _read_json_from_disk(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ensure_loaded() -> None:
    """Reload from disk if cache is cold or config.json mtime changed (or file removed)."""
    global _cache, _cache_mtime
    path = _config_path()
    if not path.exists():
        if _cache is not None and _cache_mtime is None:
            return
        _cache = {}
        _cache_mtime = None
        return

    current_mtime = path.stat().st_mtime
    if _cache is not None and _cache_mtime is not None and current_mtime == _cache_mtime:
        return

    _cache = _read_json_from_disk(path)
    _cache_mtime = current_mtime


def _persist_and_update_cache(config: dict) -> None:
    """Write config.json and refresh in-memory cache (caller must hold _lock)."""
    global _cache, _cache_mtime
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    _cache = copy.deepcopy(config)
    _cache_mtime = path.stat().st_mtime if path.exists() else None


def _load_config() -> dict:
    """Return a deep copy for mutation (e.g. setters that read-merge-write)."""
    with _lock:
        _ensure_loaded()
        return copy.deepcopy(_cache) if _cache is not None else {}


def _save_config(config: dict) -> None:
    with _lock:
        _persist_and_update_cache(config)


def get_api_key() -> str:
    with _lock:
        _ensure_loaded()
        val = (_cache or {}).get("gemini_api_key", "")
        return val if isinstance(val, str) else ""


def set_api_key(api_key: str):
    config = _load_config()
    config["gemini_api_key"] = api_key
    _save_config(config)


def get_deepl_api_key() -> str:
    with _lock:
        _ensure_loaded()
        val = (_cache or {}).get("deepl_api_key", "")
        return val if isinstance(val, str) else ""


def set_deepl_api_key(api_key: str):
    config = _load_config()
    config["deepl_api_key"] = api_key
    _save_config(config)


def get_protected_phrases() -> list[str]:
    with _lock:
        _ensure_loaded()
        raw = (_cache or {}).get("protected_phrases", [])
        if not isinstance(raw, list):
            return []
        return [p for p in raw if isinstance(p, str)]


def set_protected_phrases(phrases: list[str]):
    config = _load_config()
    cleaned = []
    for p in phrases:
        if isinstance(p, str):
            p = p.strip()
            if p:
                cleaned.append(p)
    config["protected_phrases"] = cleaned
    _save_config(config)


def get_domain_contexts() -> list[str]:
    with _lock:
        _ensure_loaded()
        cache = _cache or {}
        # Older config.json files store the list under the singular key
        # "domain_context" (the key was renamed when multiple contexts were
        # introduced). Fall back to it so those settings are not silently
        # ignored; an explicitly saved "domain_contexts" always wins.
        if "domain_contexts" in cache:
            contexts = cache["domain_contexts"]
        else:
            contexts = cache.get("domain_context", [])
    if isinstance(contexts, str):
        return [contexts] if contexts.strip() else []
    if not isinstance(contexts, list):
        return []
    return [c.strip() for c in contexts if isinstance(c, str) and c.strip()]


def get_domain_context() -> str:
    contexts = get_domain_contexts()
    return contexts[0] if contexts else ""


def set_domain_contexts(contexts: list[str]):
    config = _load_config()
    cleaned = []
    for c in contexts:
        if isinstance(c, str):
            c = c.strip()
            if c:
                cleaned.append(c)
    config["domain_contexts"] = cleaned
    config.pop("domain_context", None)  # retire the legacy singular key once migrated
    _save_config(config)


def set_domain_context(context_text: str):
    set_domain_contexts([context_text] if context_text.strip() else [])
