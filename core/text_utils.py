import html
import re

from core.constants import (
    CYRILLIC_TO_LATIN_MAP,
    DECIMAL_COMMA_LANGUAGES,
    LATIN_TO_CYRILLIC_DIGRAPHS,
    LATIN_TO_CYRILLIC_MAP,
)


def _protect_phrases(texts: list[str], phrases: list[str]) -> tuple[list[str], dict[str, str]]:
    if not phrases:
        return texts, {}

    placeholder_map = {}
    modified = list(texts)
    sorted_phrases = sorted(phrases, key=len, reverse=True)

    for phrase in sorted_phrases:
        tag = f"⟦PH{len(placeholder_map):03d}⟧"
        placeholder_map[tag] = phrase
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        for i, text in enumerate(modified):
            if pattern.search(text):
                modified[i] = pattern.sub(tag, text)

    return modified, placeholder_map


def _restore_phrases(texts: list[str], placeholder_map: dict[str, str]) -> list[str]:
    if not placeholder_map:
        return texts
    restored = []
    for text in texts:
        for tag, original in placeholder_map.items():
            text = text.replace(tag, original)
        restored.append(text)
    return restored


def _get_locale_instruction(target_lang: str) -> str:
    instructions = []
    if target_lang in DECIMAL_COMMA_LANGUAGES:
        instructions.append(
            f'For {target_lang}, use a comma as the decimal separator in translated technical values and TDS/table content (for example, "12,5"), while preserving units and spacing.'
        )
    if target_lang == "Serbian (Latin)":
        instructions.append("Write the Serbian translation in the Latin script only. Do not alter technical placeholders or XML-style formatting markers such as <r0>...</r0>.")
    elif target_lang == "Serbian (Azbuka)":
        instructions.append("Write the Serbian translation in the Cyrillic (Azbuka) script only for natural-language text. Do not alter technical placeholders or XML-style formatting markers such as <r0>...</r0>.")
    instructions.append(
        'In construction or interior-finishing contexts, translate "skirting boards" using the standard target-language term for the trim at the base of a wall, not a literal or generic flooring-strip rendering.'
    )
    return " ".join(instructions)


def _looks_like_clause_reference(text: str, match_start: int) -> bool:
    prefix = text[max(0, match_start - 24):match_start].lower()
    return bool(re.search(r"(čl|cl|clause|section|sec|article|art|bod|point|chapter|kap)\.?\s*$", prefix))


def _normalize_decimal_separators(texts: list[str], target_lang: str) -> list[str]:
    if target_lang not in DECIMAL_COMMA_LANGUAGES:
        return texts

    normalized = []
    for text in texts:
        def replace_decimal(match):
            if _looks_like_clause_reference(text, match.start()):
                return match.group(0)
            return f"{match.group(1)},{match.group(2)}"

        normalized.append(re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", replace_decimal, text))
    return normalized


def _to_serbian_latin(text: str) -> str:
    return "".join(CYRILLIC_TO_LATIN_MAP.get(char, char) for char in text)


def _to_serbian_cyrillic(text: str) -> str:
    converted = text
    for latin, cyrillic in LATIN_TO_CYRILLIC_DIGRAPHS.items():
        converted = converted.replace(latin, cyrillic)
    return "".join(LATIN_TO_CYRILLIC_MAP.get(char, char) for char in converted)


def _apply_script_variant(texts: list[str], target_lang: str) -> list[str]:
    if target_lang == "Serbian (Latin)":
        return [_to_serbian_latin(text) for text in texts]
    if target_lang == "Serbian (Azbuka)":
        return [_to_serbian_cyrillic(text) for text in texts]
    return texts


def normalize_run_tags(text: str) -> str:
    # Serbian Cyrillic transliteration can convert the ASCII tag marker "r"
    # inside formatting placeholders (<r0>...</r0>) into Cyrillic "р".
    # Normalize those markers back before the run parser consumes them.
    normalized = re.sub(r"<(/?)[рР](\d+)>", r"<\1r\2>", text)
    return re.sub(r"<(/?)R(\d+)>", r"<\1r\2>", normalized)


def _escape_xml_preserving_run_tags(text: str) -> str:
    parts = re.split(r"(<\/?r\d+>)", text)
    escaped_parts = []
    for part in parts:
        if re.fullmatch(r"<\/?r\d+>", part):
            escaped_parts.append(part)
        else:
            escaped_parts.append(html.escape(part, quote=False))
    return "".join(escaped_parts)
