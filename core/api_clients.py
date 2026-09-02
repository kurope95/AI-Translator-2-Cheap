import concurrent.futures
import json
import socket
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

from deep_translator import GoogleTranslator

from core.constants import DEEPL_LANGUAGE_CODES, GEMINI_BACKEND_MODEL_MAP, GEMINI_REQUEST_CHAR_LIMIT
from core.progress import TranslationProgress
from core.translation_memory import tm_stats_bucket, translate_with_memory
from core.text_utils import (
    _apply_script_variant,
    _escape_xml_preserving_run_tags,
    _get_locale_instruction,
    _normalize_decimal_separators,
    _protect_phrases,
    _restore_phrases,
)
from core.utils import (
    _deepl_api_base,
    _get_base_target_language,
    _get_gemini_execution_settings,
    _get_google_target_code,
    _is_gemini_backend,
    _summarize_numeric_values,
)


# ─── Google Translate Backend ────────────────────────────────

def _google_batch_translate(
    texts: list[str], target_lang: str, progress: TranslationProgress = None,
    set_total: bool = True,
) -> list[str]:
    lang_code = _get_google_target_code(target_lang)
    translator = GoogleTranslator(source="auto", target=lang_code)

    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    results = [""] * len(texts)

    for i, t in enumerate(texts):
        if not t.strip():
            results[i] = t

    batch_size = 15
    total_batches = (len(indexed) + batch_size - 1) // batch_size
    if progress and set_total:
        progress.set_total(total_batches)

    for batch_num, start in enumerate(range(0, len(indexed), batch_size)):
        batch = indexed[start : start + batch_size]
        batch_texts = [t for _, t in batch]

        translated = []
        for attempt in range(3):
            try:
                translated = translator.translate_batch(batch_texts)
                if len(translated) == len(batch_texts):
                    break
            except Exception:
                pass
            time.sleep(1 + attempt * 2)

        if not translated or len(translated) != len(batch_texts):
            raise RuntimeError("Translation failed: Free Google Translate API rejected the connection or timed out. Your IP may be rate-limited.")

        if translated == batch_texts and any(len(t) > 15 for t in batch_texts):
            raise RuntimeError("Translation failed: Free Google Translate API IP-ban detected. Google returned your original English texts without translating them. Please switch to Gemini.")

        for (orig_idx, _), trans_text in zip(batch, translated):
            original = texts[orig_idx]
            leading = original[: len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()) :]
            if trans_text:
                results[orig_idx] = leading + trans_text.strip() + trailing
            else:
                results[orig_idx] = original

        if progress:
            progress.advance()

        if start + batch_size < len(indexed):
            time.sleep(1.0)

    return _apply_script_variant(results, target_lang)


# ─── Batch Utilities ─────────────────────────────────────────

def _build_adaptive_batches(indexed, contexts, max_batch_items, max_batch_chars):
    if not indexed:
        return []
    batches = []
    current = []
    current_chars = 0
    for item in indexed:
        item_index, item_text = item
        context_text = contexts[item_index] if contexts and item_index < len(contexts) else ""
        text_len = max(1, len(item_text)) + min(240, len(context_text))
        would_exceed_items = len(current) >= max_batch_items
        would_exceed_chars = current and (current_chars + text_len > max_batch_chars)
        if would_exceed_items or would_exceed_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += text_len
    if current:
        batches.append(current)
    return batches


def _estimate_adaptive_batch_chars(batch, contexts):
    total = 0
    for item_index, item_text in batch:
        context_text = contexts[item_index] if contexts and item_index < len(contexts) else ""
        total += max(1, len(item_text)) + min(240, len(context_text))
    return total


def _extract_json_array_candidate(response_text):
    text = response_text.strip().replace("﻿", "")
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].strip()
    first = text.find("[")
    last = text.rfind("]")
    if first != -1 and last != -1 and last > first:
        return text[first:last + 1]
    return text


def _iter_json_array_candidates(response_text):
    text = response_text.strip().replace("﻿", "")
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].strip()

    decoder = json.JSONDecoder()
    candidates = []
    for start, ch in enumerate(text):
        if ch != "[":
            continue
        try:
            parsed, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            candidates.append(text[start:start + end])
    compact = _extract_json_array_candidate(text)
    if compact and compact not in candidates:
        candidates.append(compact)
    return candidates


def _parse_translation_array(response_text, expected_len):
    last_error = None
    for idx, candidate in enumerate(_iter_json_array_candidates(response_text)):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            try:
                repaired = (
                    candidate.replace("“", '"').replace("”", '"')
                    .replace("‘", "'").replace("’", "'")
                )
                parsed = json.loads(repaired)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
        if isinstance(parsed, list) and len(parsed) == expected_len:
            return [str(x) for x in parsed], idx > 0
        last_error = ValueError(
            f"JSON array length ({len(parsed) if isinstance(parsed, list) else 'not a list'}) "
            f"does not match batch size ({expected_len})"
        )
    if last_error is not None:
        raise last_error
    raise ValueError("No JSON array found in model response.")


def _is_transient_error(exc):
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    message = str(exc).lower()
    transient_tokens = (
        "429", "503", "502", "504", "rate limit", "resource exhausted",
        "temporarily unavailable", "timeout", "timed out", "deadline exceeded",
        "connection reset", "connection aborted", "network", "unavailable",
    )
    return any(token in message for token in transient_tokens)


def _update_gemini_usage(telemetry_bucket, response):
    usage = getattr(response, "usage_metadata", None) or getattr(response, "usageMetadata", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usageMetadata") or response.get("usage_metadata")
    if usage is None:
        return
    prompt_tokens    = getattr(usage, "prompt_token_count", None)
    candidate_tokens = getattr(usage, "candidates_token_count", None)
    total_tokens     = getattr(usage, "total_token_count", None)
    thinking_tokens  = getattr(usage, "thoughts_token_count", None)
    if prompt_tokens is None and isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_token_count") or usage.get("promptTokenCount")
    if candidate_tokens is None and isinstance(usage, dict):
        candidate_tokens = usage.get("candidates_token_count") or usage.get("candidatesTokenCount")
    if total_tokens is None and isinstance(usage, dict):
        total_tokens = usage.get("total_token_count") or usage.get("totalTokenCount")
    if thinking_tokens is None and isinstance(usage, dict):
        thinking_tokens = usage.get("thoughts_token_count") or usage.get("thoughtsTokenCount")
    pt = int(prompt_tokens or 0)
    ct = int(candidate_tokens or 0)
    tt = int(total_tokens or 0)
    ht = int(thinking_tokens or 0)
    # Derive thinking tokens from the gap if the API didn't report them separately.
    # Gemini thinking models send total_tokens = prompt + completion + thinking,
    # but sometimes only expose thoughts_token_count at a different path.
    if ht == 0 and tt > pt + ct:
        ht = tt - pt - ct
    telemetry_bucket["prompt_tokens"]    += pt
    telemetry_bucket["completion_tokens"] += ct
    telemetry_bucket["total_tokens"]      += tt
    telemetry_bucket["thinking_tokens"]   += ht


# ─── Gemini Flash Backend ────────────────────────────────────

def _gemini_batch_translate(
    texts, target_lang, api_key,
    protected_phrases=None, progress=None,
    model_name="gemini-3-flash-preview", domain_context="",
    max_workers=20, batch_size=30, telemetry=None,
    contexts=None,
    set_total=True,
    temperature=None,
):
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=api_key)
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    results = [""] * len(texts)

    for i, t in enumerate(texts):
        if not t.strip():
            results[i] = t

    dnt_instruction = ""
    if protected_phrases:
        phrases_list = ", ".join(f'"{p}"' for p in protected_phrases)
        dnt_instruction = f"""
CRITICAL: The following phrases must NOT be translated — keep them EXACTLY as they are in the original language: {phrases_list}
These are technical terms, testing method names, or brand names. Only protect the exact phrase/sequence, not individual words when used separately."""

    batches = _build_adaptive_batches(
        indexed,
        contexts or [],
        max_batch_items=batch_size,
        max_batch_chars=GEMINI_REQUEST_CHAR_LIMIT,
    )

    batch_item_counts = [len(batch) for batch in batches]
    batch_char_counts = [_estimate_adaptive_batch_chars(batch, contexts or []) for batch in batches]

    telemetry_bucket = None
    if telemetry is not None:
        telemetry_bucket = telemetry.setdefault("gemini", {})
        for key in ("batches", "api_calls", "retries", "attempts_total",
                     "parse_recoveries", "failed_batches", "prompt_tokens",
                     "completion_tokens", "thinking_tokens", "total_tokens"):
            telemetry_bucket.setdefault(key, 0)
        telemetry_bucket.setdefault("model", model_name)
        telemetry_bucket.setdefault("batch_item_limit", batch_size)
        telemetry_bucket.setdefault("batch_char_limit", GEMINI_REQUEST_CHAR_LIMIT)
        telemetry_bucket.setdefault("max_workers", max_workers)
        telemetry_bucket.setdefault("invocations", 0)
        telemetry_bucket.setdefault("request_batches_total", 0)
        telemetry_bucket.setdefault("request_item_observations", [])
        telemetry_bucket.setdefault("request_char_observations", [])
        telemetry_bucket["max_workers"] = max_workers
        telemetry_bucket["batch_item_limit"] = batch_size
        telemetry_bucket["batch_char_limit"] = GEMINI_REQUEST_CHAR_LIMIT

    total_batches = len(batches)
    if progress and set_total:
        progress.set_total(total_batches)
    if telemetry_bucket is not None:
        telemetry_bucket["batches"] += total_batches
        telemetry_bucket["invocations"] += 1
        telemetry_bucket["request_batches_total"] += total_batches
        telemetry_bucket["request_item_observations"].extend(batch_item_counts)
        telemetry_bucket["request_char_observations"].extend(batch_char_counts)
        telemetry_bucket["request_item_stats"] = _summarize_numeric_values(
            telemetry_bucket["request_item_observations"]
        )
        telemetry_bucket["request_char_stats"] = _summarize_numeric_values(
            telemetry_bucket["request_char_observations"]
        )

    def process_batch(batch_tuple):
        batch_num, batch = batch_tuple
        batch_texts = [t for _, t in batch]

        numbered_lines_parts = []
        for i, text in enumerate(batch_texts):
            orig_idx = batch[i][0]
            ctx = ""
            if contexts and orig_idx < len(contexts):
                ctx = (contexts[orig_idx] or "").strip()
            if ctx:
                numbered_lines_parts.append(f"[{i}]\nTEXT: {text}\nCONTEXT: {ctx}")
            else:
                numbered_lines_parts.append(f"[{i}]\nTEXT: {text}")
        numbered_lines = "\n".join(numbered_lines_parts)

        domain_instruction = ""
        if domain_context:
            domain_instruction = f"You are an expert technical translator specializing in Technical Data Sheets (TDS) for {domain_context}. Use appropriate industrial jargon."
        locale_instruction = _get_locale_instruction(target_lang)
        prompt_target_lang = _get_base_target_language(target_lang)

        prompt = f"""You are a professional translator. {domain_instruction} Translate the following text segments from their original language into {prompt_target_lang}.

CRITICAL RULES:
1. Return ONLY a JSON array of translated strings, in the exact same order.
2. IMPORTANT: Each input string may contain XML tags like <r0>, <r1>, etc. You MUST preserve these exact XML tags in your translation at the appropriate locations to maintain formatting. Do NOT remove or alter the <rX>...</rX> wrappers.
3. Preserve the EXACT meaning, tone, and register of the original.
4. Use proper {prompt_target_lang} grammar, idioms, and natural phrasing. Prefer native professional collocations over literal source-language wording.
5. Do NOT translate proper nouns, brand names, product names, or chemical formulas.
6. Do NOT add explanations or notes — only the translations.
7. Preserve any numbers, units, and formatting gaps. However, do NOT strictly force English punctuation (like hyphens in compound words) into the translation if the target language natively writes the word without a hyphen.
8. Each item in your response array must correspond to the same index in the input.
9. Locale and terminology guidance: {locale_instruction}
10. Some items have a «...» context annotation after the text — use it to understand terminology and tone, but translate ONLY the text before «. Do NOT include the annotation in your output.
{dnt_instruction}

Input segments:
{numbered_lines}

Respond with ONLY a JSON array like ["translated with <r0>tags</r0>", "translation2", ...]. No markdown block, no explanation."""

        translated_batch = [""] * len(batch_texts)
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            try:
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")

                socket.setdefaulttimeout(120)

                if telemetry_bucket is not None:
                    telemetry_bucket["api_calls"] += 1
                    telemetry_bucket["attempts_total"] += 1

                gen_config_kwargs = {}
                if temperature is not None:
                    gen_config_kwargs["temperature"] = temperature
                gen_config = genai_types.GenerateContentConfig(**gen_config_kwargs) if gen_config_kwargs else None

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    **(dict(config=gen_config) if gen_config is not None else {}),
                )
                if telemetry_bucket is not None:
                    _update_gemini_usage(telemetry_bucket, response)

                response_text = (response.text or "").strip()
                translated_batch, recovered = _parse_translation_array(response_text, len(batch_texts))
                if telemetry_bucket is not None and recovered:
                    telemetry_bucket["parse_recoveries"] += 1
                break
            except Exception as e:
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")
                last_error = e
                if _is_transient_error(e) and attempt < max_attempts - 1:
                    if telemetry_bucket is not None:
                        telemetry_bucket["retries"] += 1
                    time.sleep((2 ** attempt) + 1)
                    continue
                if telemetry_bucket is not None:
                    telemetry_bucket["failed_batches"] += 1
                raise RuntimeError(
                    f"Translation failed in batch {batch_num + 1}/{total_batches}: {type(e).__name__}: {e}"
                ) from e

        if last_error is not None and translated_batch == [""] * len(batch_texts):
            if telemetry_bucket is not None:
                telemetry_bucket["failed_batches"] += 1
            raise RuntimeError(
                f"Translation failed in batch {batch_num + 1}/{total_batches}: {type(last_error).__name__}: {last_error}"
            )

        if progress and progress.is_cancelled:
            raise RuntimeError("Translation cancelled by user.")

        for (orig_idx, _), trans_text in zip(batch, translated_batch):
            original = texts[orig_idx]
            leading = original[: len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()) :]
            if trans_text:
                results[orig_idx] = leading + trans_text.strip() + trailing
            else:
                results[orig_idx] = original

        if progress:
            progress.advance()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_batch, (i, b)): i for i, b in enumerate(batches)}
        for future in concurrent.futures.as_completed(futures, timeout=1800):
            future.result()

    if telemetry_bucket is not None:
        total_b = max(1, telemetry_bucket["request_batches_total"])
        telemetry_bucket["avg_attempts_per_batch"] = round(
            telemetry_bucket["attempts_total"] / total_b, 3
        )

    return _apply_script_variant(results, target_lang)


# ─── DeepL Backend ───────────────────────────────────────────

def _deepl_batch_translate(
    texts: list[str], target_lang: str, api_key: str,
    protected_phrases: list[str] = None, progress: TranslationProgress = None,
    domain_context: str = "", batch_size: int = 8,
    set_total: bool = True,
) -> list[str]:
    import html as html_module

    target_code = DEEPL_LANGUAGE_CODES.get(_get_base_target_language(target_lang))
    if not target_code:
        raise RuntimeError(f"DeepL does not support {target_lang} in this app yet.")

    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    results = [""] * len(texts)

    for i, t in enumerate(texts):
        if not t.strip():
            results[i] = t

    context_parts = []
    if domain_context:
        context_parts.append(f"Domain: {domain_context}.")
    locale_instruction = _get_locale_instruction(target_lang)
    if locale_instruction:
        context_parts.append(locale_instruction)
    deepl_context = " ".join(context_parts)

    total_batches = (len(indexed) + batch_size - 1) // batch_size
    if progress and set_total:
        progress.set_total(total_batches)

    for batch_num, start in enumerate(range(0, len(indexed), batch_size), start=1):
        batch = indexed[start : start + batch_size]
        batch_texts = [_escape_xml_preserving_run_tags(t) for _, t in batch]
        payload = {
            "text": batch_texts,
            "target_lang": target_code,
            "tag_handling": "xml",
            "outline_detection": False,
            "preserve_formatting": True,
        }
        if deepl_context:
            payload["context"] = deepl_context

        success = False
        translated_batch = [""] * len(batch_texts)

        for attempt in range(4):
            try:
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")

                req = urllib_request.Request(
                    f"{_deepl_api_base(api_key)}/v2/translate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"DeepL-Auth-Key {api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=120) as response:
                    response_data = json.loads(response.read().decode("utf-8"))

                translated_batch = [
                    html_module.unescape(item["text"]) for item in response_data.get("translations", [])
                ]
                if len(translated_batch) != len(batch_texts):
                    raise ValueError("DeepL returned a different number of translations than requested.")
                success = True
                break
            except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")
                time.sleep((2 ** attempt) + 1)

        if not success:
            raise RuntimeError("Translation failed: DeepL API rejected the content or failed to return valid output after 4 attempts.")

        for (orig_idx, _), trans_text in zip(batch, translated_batch):
            original = texts[orig_idx]
            leading = original[: len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()) :]
            if trans_text:
                results[orig_idx] = leading + trans_text.strip() + trailing
            else:
                results[orig_idx] = original

        if progress:
            progress.advance()

    return _apply_script_variant(results, target_lang)


# ─── Legacy Gemini Backend ───────────────────────────────────

def _legacy_gemini_batch_translate(
    texts: list[str],
    target_lang: str,
    api_key: str,
    protected_phrases: list[str] | None = None,
    progress: TranslationProgress | None = None,
    model_name: str = "gemini-3-flash-preview",
    domain_context: str = "",
    max_workers: int = 20,
    batch_size: int = 15,
    telemetry: dict | None = None,
) -> list[str]:
    from google import genai

    client = genai.Client(api_key=api_key)
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    results = [""] * len(texts)

    for i, text in enumerate(texts):
        if not text.strip():
            results[i] = text

    telemetry_bucket = None
    if telemetry is not None:
        telemetry_bucket = telemetry.setdefault("gemini_legacy", {})
        for key in ("batches", "api_calls", "retries", "attempts_total",
                     "parse_recoveries", "failed_batches", "prompt_tokens",
                     "completion_tokens", "thinking_tokens", "total_tokens"):
            telemetry_bucket.setdefault(key, 0)
        telemetry_bucket.setdefault("model", model_name)
        telemetry_bucket.setdefault("batch_item_limit", batch_size)
        telemetry_bucket.setdefault("max_workers", max_workers)

    dnt_instruction = ""
    if protected_phrases:
        phrases_list = ", ".join(f'"{phrase}"' for phrase in protected_phrases)
        dnt_instruction = f"""
CRITICAL: The following phrases must NOT be translated - keep them EXACTLY as they are in the original language: {phrases_list}
These are technical terms, testing method names, or brand names. Only protect the exact phrase/sequence, not individual words when used separately."""

    batches = []
    for start in range(0, len(indexed), batch_size):
        batches.append(indexed[start : start + batch_size])

    total_batches = len(batches)
    if progress:
        progress.set_total(total_batches)

    if telemetry_bucket is not None:
        telemetry_bucket["batches"] += total_batches

    def process_batch(batch_tuple):
        batch_num, batch = batch_tuple
        batch_texts = [text for _, text in batch]
        numbered_lines = "\n".join(f"[{i}] {text}" for i, text in enumerate(batch_texts))

        domain_instruction = ""
        if domain_context:
            domain_instruction = (
                f"You are an expert technical translator specializing in Technical Data Sheets (TDS) for {domain_context}. "
                "Use appropriate industrial jargon."
            )
        locale_instruction = _get_locale_instruction(target_lang)
        prompt_target_lang = _get_base_target_language(target_lang)

        prompt = f"""You are a professional translator. {domain_instruction} Translate the following text segments from their original language into {prompt_target_lang}.

CRITICAL RULES:
1. Return ONLY a JSON array of translated strings, in the exact same order.
2. IMPORTANT: Each input string may contain XML tags like <r0>, <r1>, etc. You MUST preserve these exact XML tags in your translation at the appropriate locations to maintain formatting. Do NOT remove or alter the <rX>...</rX> wrappers.
3. Preserve the EXACT meaning, tone, and register of the original.
4. Use proper {prompt_target_lang} grammar, idioms, and natural phrasing.
5. Do NOT translate proper nouns, brand names, product names, or chemical formulas.
6. Do NOT add explanations or notes - only the translations.
7. Preserve any numbers, units, and formatting gaps. However, do NOT strictly force English punctuation (like hyphens in compound words) into the translation if the target language natively writes the word without a hyphen.
8. Each item in your response array must correspond to the same index in the input.
9. Locale and terminology guidance: {locale_instruction}
{dnt_instruction}

Input segments:
{numbered_lines}

Respond with ONLY a JSON array like ["translated with <r0>tags</r0>", "translation2", ...]. No markdown block, no explanation."""

        translated_batch = [""] * len(batch_texts)
        success = False

        for attempt in range(4):
            try:
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")

                socket.setdefaulttimeout(120)

                if telemetry_bucket is not None:
                    telemetry_bucket["api_calls"] += 1
                    telemetry_bucket["attempts_total"] += 1

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if telemetry_bucket is not None:
                    _update_gemini_usage(telemetry_bucket, response)

                response_text = (response.text or "").strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("\n", 1)[1]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3].strip()

                parsed_array = json.loads(response_text)
                if isinstance(parsed_array, list) and len(parsed_array) == len(batch_texts):
                    translated_batch = parsed_array
                    success = True
                    break
                raise ValueError(
                    f"JSON array length ({len(parsed_array) if isinstance(parsed_array, list) else 'not a list'}) "
                    f"does not match batch size ({len(batch_texts)})"
                )
            except Exception:
                if progress and progress.is_cancelled:
                    raise RuntimeError("Translation cancelled by user.")
                if telemetry_bucket is not None:
                    telemetry_bucket["retries"] += 1
                time.sleep((2 ** attempt) + 1)

        if not success:
            if telemetry_bucket is not None:
                telemetry_bucket["failed_batches"] += 1
            raise RuntimeError(
                "Translation failed: Google API rejected the content or failed to return valid JSON after 4 attempts."
            )

        if progress and progress.is_cancelled:
            raise RuntimeError("Translation cancelled by user.")

        for (orig_idx, _), trans_text in zip(batch, translated_batch):
            original = texts[orig_idx]
            leading = original[: len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()) :]
            results[orig_idx] = leading + trans_text.strip() + trailing if trans_text else original

        if progress:
            progress.advance(f"Translating batch {progress.completed_steps + 1}/{total_batches}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_batch, (i, batch)): i for i, batch in enumerate(batches)}
        for future in concurrent.futures.as_completed(futures, timeout=1800):
            future.result()

    if telemetry_bucket is not None:
        total_b = max(1, telemetry_bucket["batches"])
        telemetry_bucket["avg_attempts_per_batch"] = round(
            telemetry_bucket["attempts_total"] / total_b, 3
        )

    return _apply_script_variant(results, target_lang)


# ─── Translation Dispatcher ──────────────────────────────────

def _batch_translate(
    texts, target_lang,
    backend="google", api_key="",
    protected_phrases=None, progress=None,
    domain_context="", telemetry=None,
    contexts=None,
    set_total=True,
    temperature=None,
):
    tm_stats = tm_stats_bucket(telemetry)
    if (not _is_gemini_backend(backend) and backend != "deepl") or not api_key:
        protected, pmap = _protect_phrases(texts, protected_phrases or [])
        fused = translate_with_memory(
            protected,
            target_lang,
            tm_stats,
            lambda sub, _ctx: _google_batch_translate(sub, target_lang, progress, set_total=set_total),
            progress,
            contexts=None,
        )
        results = _restore_phrases(fused, pmap)
        return _normalize_decimal_separators(results, target_lang)
    if backend == "deepl":
        protected, pmap = _protect_phrases(texts, protected_phrases or [])
        fused = translate_with_memory(
            protected,
            target_lang,
            tm_stats,
            lambda sub, _ctx: _deepl_batch_translate(
                sub, target_lang, api_key, protected_phrases, progress,
                domain_context=domain_context, batch_size=8, set_total=set_total,
            ),
            progress,
            contexts=None,
        )
        results = _restore_phrases(fused, pmap)
        return _normalize_decimal_separators(results, target_lang)

    model_name = GEMINI_BACKEND_MODEL_MAP.get(backend, GEMINI_BACKEND_MODEL_MAP["gemini"])
    execution_settings = _get_gemini_execution_settings(backend)
    workers = execution_settings["max_workers"]
    bsize = execution_settings["request_item_limit"]

    results = translate_with_memory(
        texts,
        target_lang,
        tm_stats,
        lambda sub, ctx_slice: _gemini_batch_translate(
            sub, target_lang, api_key, protected_phrases, progress,
            model_name=model_name, domain_context=domain_context,
            max_workers=workers, batch_size=bsize, telemetry=telemetry,
            contexts=(ctx_slice if ctx_slice is not None else contexts),
            set_total=set_total,
            temperature=temperature,
        ),
        progress,
        contexts=contexts,
    )
    return _normalize_decimal_separators(results, target_lang)


def legacy_batch_translate(
    texts: list[str],
    target_lang: str,
    backend: str = "google",
    api_key: str = "",
    protected_phrases: list[str] | None = None,
    progress: TranslationProgress | None = None,
    domain_context: str = "",
    telemetry: dict | None = None,
    skip_decimal_normalization: bool = False,
) -> list[str]:
    tm_stats = tm_stats_bucket(telemetry)
    normalize = lambda r: (
        r if skip_decimal_normalization else _normalize_decimal_separators(r, target_lang)
    )

    if (not _is_gemini_backend(backend) and backend != "deepl") or not api_key:
        protected, phrase_map = _protect_phrases(texts, protected_phrases or [])
        fused = translate_with_memory(
            protected,
            target_lang,
            tm_stats,
            lambda sub, _ctx: _google_batch_translate(sub, target_lang, progress),
            progress,
            contexts=None,
        )
        return normalize(_restore_phrases(fused, phrase_map))

    if backend == "deepl":
        protected, phrase_map = _protect_phrases(texts, protected_phrases or [])
        fused = translate_with_memory(
            protected,
            target_lang,
            tm_stats,
            lambda sub, _ctx: _deepl_batch_translate(
                sub,
                target_lang,
                api_key,
                protected_phrases,
                progress,
                domain_context=domain_context,
                batch_size=8,
            ),
            progress,
            contexts=None,
        )
        return normalize(_restore_phrases(fused, phrase_map))

    model_name = GEMINI_BACKEND_MODEL_MAP[backend]

    def _legacy_gem_workers(w: int, b: int):
        def _runner(sub: list[str], _ctx=None):
            return _legacy_gemini_batch_translate(
                sub, target_lang, api_key, protected_phrases, progress,
                model_name=model_name, domain_context=domain_context,
                max_workers=w, batch_size=b, telemetry=telemetry,
            )

        return _runner

    if backend in {"gemini", "gemini-25-flash", "gemini-37-flash"}:
        results = translate_with_memory(
            texts, target_lang, tm_stats,
            _legacy_gem_workers(10, 12), progress, contexts=None,
        )
    elif backend == "gemini-35-flash-lite":
        results = translate_with_memory(
            texts, target_lang, tm_stats,
            _legacy_gem_workers(12, 12), progress, contexts=None,
        )
    else:
        results = translate_with_memory(
            texts, target_lang, tm_stats,
            _legacy_gem_workers(20, 15), progress, contexts=None,
        )

    return normalize(results)
