"""
HTML Translator
Translates .html files while preserving HTML tags, attributes, and structure.
Uses the Legacy translation engine.
"""

import os
import re
import time
from pathlib import Path

from core.api_clients import legacy_batch_translate
from core.config import get_protected_phrases
from core.constants import FINALIZATION_PROGRESS_STEPS
from core.progress import TranslationProgress


_INLINE_TAGS = {
    "a", "abbr", "b", "bdi", "bdo", "cite", "code", "del", "dfn", "em",
    "i", "ins", "kbd", "mark", "q", "rp", "rt", "ruby", "s", "samp",
    "small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr",
}


def _collect_text_nodes_from_html(html: str) -> tuple[list[dict], str]:
    """
    Walk HTML and collect translatable text content.
    Returns (segments, html_with_placeholders) where each segment has
    an index and preserves surrounding tag context.
    """
    # Strategy: extract translatable text from <title>, <meta content>,
    # and actual text nodes in <body>. Use simple regex-based extraction
    # to avoid a full parser dependency for basic cases.
    segments = []
    placeholder_text = html

    # Extract <title> content
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if title_match and title_match.group(1).strip():
        tag = f"\x00HTMLTITLE\x00"
        segments.append({"type": "title", "text": title_match.group(1).strip(), "tag": tag})
        placeholder_text = placeholder_text.replace(title_match.group(0), f"<title>{tag}</title>", 1)

    # Extract meta description/content
    for meta_match in re.finditer(
        r'<meta[^>]*(?:name|property)\s*=\s*["\'](?:description|og:description)["\'][^>]*content\s*=\s*["\']([^"\']*)["\'][^>]*/?>',
        html, re.IGNORECASE
    ):
        if meta_match.group(1).strip():
            tag = f"\x00HTMLMETA{len(segments)}\x00"
            content = meta_match.group(1).strip()
            segments.append({"type": "meta_description", "text": content, "tag": tag})
            old = meta_match.group(0)
            new = old.replace(f'content="{content}"', f'content="{tag}"')
            placeholder_text = placeholder_text.replace(old, new, 1)

    # Extract alt attributes
    for alt_match in re.finditer(
        r'<img[^>]*alt\s*=\s*["\']([^"\']*)["\'][^>]*/?>', html, re.IGNORECASE
    ):
        if alt_match.group(1).strip():
            tag = f"\x00HTMLALT{len(segments)}\x00"
            content = alt_match.group(1).strip()
            segments.append({"type": "alt", "text": content, "tag": tag})
            old = alt_match.group(0)
            new = old.replace(f'alt="{content}"', f'alt="{tag}"')
            placeholder_text = placeholder_text.replace(old, new, 1)

    # Extract body text content - walking between tags
    body_match = re.search(r"<body[^>]*>", placeholder_text, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_start = body_match.end()
        body_end_match = re.search(r"</body>", placeholder_text[body_start:], re.IGNORECASE)
        body_end = body_start + (body_end_match.start() if body_end_match else len(placeholder_text) - body_start)
        body_content = placeholder_text[body_start:body_end]

        # Split body into segments by tag boundaries
        # Collect text between tags that has actual content
        text_parts = re.split(r"<[^>]*>", body_content)
        idx = 0
        for part in text_parts:
            stripped = part.strip()
            if stripped and any(c.isalpha() for c in stripped):
                tag = f"\x00HTMLBODY{idx}\x00"
                segments.append({"type": "body_text", "text": stripped, "tag": tag, "index": idx})
                placeholder_text = placeholder_text.replace(stripped, tag, 1)
                idx += 1

    return segments, placeholder_text


def _restore_html_text(text: str, segment_map: dict[str, str]) -> str:
    """Restore HTML placeholders back to original translated text."""
    if not segment_map:
        return text
    for tag, original in sorted(segment_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(tag, original)
    return text


def translate_html(
    input_path: str,
    output_path: str,
    target_lang: str,
    backend: str = "google",
    api_key: str = "",
    progress: TranslationProgress = None,
    domain_context: str = "",
    telemetry: dict | None = None,
) -> str:
    if progress is None:
        progress = TranslationProgress()
    progress.reset()
    progress.set_phase("Preparing HTML...")

    job_started_at = time.perf_counter()
    phrases = get_protected_phrases()
    telemetry = telemetry if telemetry is not None else {}
    telemetry.setdefault("timings", {})
    telemetry.setdefault("document", {})

    load_started_at = time.perf_counter()
    with open(input_path, "r", encoding="utf-8") as f:
        raw_html = f.read()
    telemetry["timings"]["load_html_seconds"] = round(time.perf_counter() - load_started_at, 3)

    telemetry["document"].update({
        "document_mode": "html",
        "backend": backend,
        "char_count": len(raw_html),
    })

    # Collect text content and replace with placeholders
    progress.set_phase("Extracting text from HTML...")
    extract_started_at = time.perf_counter()
    segments, html_with_placeholders = _collect_text_nodes_from_html(raw_html)
    telemetry["timings"]["extract_html_seconds"] = round(time.perf_counter() - extract_started_at, 3)

    texts = [s["text"] for s in segments]
    segment_map = {s["tag"]: None for s in segments}  # will fill with translations

    non_empty = [t for t in texts if t.strip()]
    if not non_empty:
        progress.set_phase("No translatable text found.")
        progress.advance("Complete")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(raw_html)
        telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)
        return output_path

    estimated_batches = (len(non_empty) + 11) // 12
    total_steps = estimated_batches + FINALIZATION_PROGRESS_STEPS
    progress.set_total(max(1, total_steps))

    telemetry["document"].update({
        "html_text_unit_count": len(segments),
        "html_non_empty_count": len(non_empty),
        "estimated_total_steps": total_steps,
    })

    progress.set_phase("Translating HTML...")
    translation_started_at = time.perf_counter()

    translated_texts = legacy_batch_translate(
        texts,
        target_lang,
        backend,
        api_key,
        phrases,
        progress,
        domain_context,
        telemetry=telemetry,
        skip_decimal_normalization=True,
    )

    telemetry["timings"]["translate_html_seconds"] = round(time.perf_counter() - translation_started_at, 3)

    # Restore translations into HTML
    progress.set_phase("Reassembling HTML...")
    reassemble_started_at = time.perf_counter()
    for seg, trans in zip(segments, translated_texts):
        segment_map[seg["tag"]] = trans if trans else seg["text"]

    # Apply translations to html_with_placeholders
    result_html = html_with_placeholders
    for seg in segments:
        translated = segment_map.get(seg["tag"], seg["text"])
        if translated:
            result_html = result_html.replace(seg["tag"], translated, 1)

    telemetry["timings"]["reassemble_html_seconds"] = round(time.perf_counter() - reassemble_started_at, 3)

    progress.set_phase("Saving HTML...")
    save_started_at = time.perf_counter()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result_html)
    telemetry["timings"]["save_html_seconds"] = round(time.perf_counter() - save_started_at, 3)
    telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)

    progress.advance("Translation complete")
    return output_path
