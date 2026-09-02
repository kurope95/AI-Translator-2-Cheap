"""
Markdown Translator
Translates .md files while preserving markdown syntax, code blocks, and inline formatting.
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


# ─── Markdown syntax protection ──────────────────────────────
#
# Before translation, we replace markdown syntax tokens with
# placeholders so the LLM doesn't alter them. After translation
# we restore them.

_MD_PATTERNS = [
    # Code blocks (fenced)
    (r"```[\s\S]*?```", None),
    # Inline code
    (r"`[^`\n]+`", None),
    # Images ![alt](url)
    (r"!\[([^\]]*)\]\([^)]+\)", r"![{ph}]()"),
    # Links [text](url)
    (r"\[([^\]]+)\]\([^)]+\)", r"[{ph}]()"),
    # Heading markers at line start
    (r"^#{1,6}\s", None),
    # Bold **text** or __text__
    (r"\*\*[^\*]+\*\*", None),
    (r"__[^_]+__", None),
    # Emphasis *text* or _text_
    (r"(?<!\*)\*[^\*\n]+\*(?!\*)", None),
    (r"(?<!_)_[^_\n]+_(?!_)", None),
    # Horizontal rules
    (r"^---$", None),
    (r"^\*\*\*$", None),
    # Blockquotes
    (r"^>\s?", None),
    # Unordered list markers
    (r"^[\s]*[-*+]\s", None),
    # Ordered list markers
    (r"^\s*\d+\.\s", None),
]


def _protect_md(text: str) -> tuple[str, dict[str, str]]:
    """Replace markdown syntax markers with placeholders before translation."""
    placeholder_map = {}
    protected_text = text

    for idx, (pattern, _) in enumerate(_MD_PATTERNS):
        tag_prefix = f"\x00MD{idx:02d}\x00"

        def make_replacer(tag_prefix=tag_prefix, ph_map=placeholder_map):
            count = [0]

            def replacer(match):
                full = match.group(0)
                key = f"{tag_prefix}{count[0]:04d}"
                count[0] += 1
                ph_map[key] = full
                return key

            return replacer

        protected_text = re.sub(pattern, make_replacer(tag_prefix), protected_text)

    return protected_text, placeholder_map


def _restore_md(text: str, placeholder_map: dict[str, str]) -> str:
    """Restore markdown placeholders back to original syntax."""
    if not placeholder_map:
        return text
    for key, original in sorted(placeholder_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(key, original)
    return text


def translate_markdown(
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
    progress.set_phase("Preparing markdown...")

    job_started_at = time.perf_counter()
    phrases = get_protected_phrases()
    telemetry = telemetry if telemetry is not None else {}
    telemetry.setdefault("timings", {})
    telemetry.setdefault("document", {})

    load_started_at = time.perf_counter()
    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    telemetry["timings"]["load_md_seconds"] = round(time.perf_counter() - load_started_at, 3)

    telemetry["document"].update({
        "document_mode": "markdown",
        "backend": backend,
        "char_count": len(raw_text),
    })

    # Protect markdown syntax
    progress.set_phase("Protecting formatting...")
    protect_started_at = time.perf_counter()
    protected_text, md_ph_map = _protect_md(raw_text)
    telemetry["timings"]["protect_md_seconds"] = round(time.perf_counter() - protect_started_at, 3)

    # Split into paragraphs for batch translation
    paragraphs = protected_text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs]
    non_empty = [p for p in paragraphs if p.strip()]

    if not non_empty:
        progress.set_phase("No translatable text found.")
        progress.advance("Complete")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)
        return output_path

    estimated_batches = (len(non_empty) + 11) // 12
    total_steps = estimated_batches + FINALIZATION_PROGRESS_STEPS
    progress.set_total(max(1, total_steps))

    telemetry["document"].update({
        "md_paragraph_count": len(paragraphs),
        "md_non_empty_count": len(non_empty),
        "estimated_total_steps": total_steps,
    })

    progress.set_phase("Translating markdown...")
    translation_started_at = time.perf_counter()

    translated_texts = legacy_batch_translate(
        paragraphs,
        target_lang,
        backend,
        api_key,
        phrases,
        progress,
        domain_context,
        telemetry=telemetry,
        skip_decimal_normalization=True,
    )

    telemetry["timings"]["translate_md_seconds"] = round(time.perf_counter() - translation_started_at, 3)

    # Restore markdown syntax
    progress.set_phase("Restoring formatting...")
    restore_started_at = time.perf_counter()
    restored = [_restore_md(t, md_ph_map) if t else t for t in translated_texts]
    output_text = "\n\n".join(restored)
    telemetry["timings"]["restore_md_seconds"] = round(time.perf_counter() - restore_started_at, 3)

    progress.set_phase("Saving markdown...")
    save_started_at = time.perf_counter()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)
    telemetry["timings"]["save_md_seconds"] = round(time.perf_counter() - save_started_at, 3)
    telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)

    progress.advance("Translation complete")
    return output_path
