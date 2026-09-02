"""
PDF Translator — annotation-based approach.

Instead of replacing text (which requires font substitution), the original
PDF is kept intact.  Translatable text gets a red strikethrough annotation
and a popup comment containing the translation.

Text is collected at LINE level (all spans on a line merged into one unit),
then consecutive same-format lines are grouped into PARAGRAPHS for
translation with full sentence context.

Uses the Legacy translation engine (core/api_clients legacy_batch_translate).
"""

import os, re, time

import fitz  # PyMuPDF

from core.api_clients import legacy_batch_translate
from core.config import get_protected_phrases
from core.constants import FINALIZATION_PROGRESS_STEPS
from core.progress import TranslationProgress

_ALPHA_RE = re.compile(r"[a-zA-ZÀ-öø-ÿ]{3,}")
_NONWS_RE = re.compile(r"\S")


def _is_translatable(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 3:
        return False
    if not _ALPHA_RE.search(stripped):
        return False
    nonws = len(_NONWS_RE.findall(stripped))
    if nonws == 0:
        return False
    alpha_count = sum(1 for c in stripped if c.isalpha())
    return (alpha_count / nonws) >= 0.50


def _int_to_rgb(color_int: int) -> tuple:
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    return (r, g, b)


def _is_smallcaps_line(spans: list[dict]) -> bool:
    visible = [s for s in spans if s.get("text", "").strip()]
    if len(visible) < 2:
        return False
    sizes = set(s["size"] for s in visible)
    if len(sizes) < 2:
        return False
    text = "".join(s.get("text", "") for s in visible).strip()
    alpha = [c for c in text if c.isalpha()]
    return len(alpha) >= 2 and all(c.isupper() for c in alpha)


def _merge_line(spans: list[dict]) -> dict | None:
    """Merge all spans on a line into a single dict.  Returns None if not translatable."""
    if not spans:
        return None

    if _is_smallcaps_line(spans):
        merged_text = "".join(s.get("text", "") for s in spans).strip()
        if not _is_translatable(merged_text):
            return None
        visible = [s for s in spans if s.get("text", "").strip()]
        rects = [fitz.Rect(s["bbox"]) for s in visible]
        rect = fitz.Rect(
            min(r.x0 for r in rects),
            min(r.y0 for r in rects),
            max(r.x1 for r in rects),
            max(r.y1 for r in rects),
        )
        first = visible[0]
        raw = first.get("origin")
        origin = fitz.Point(raw) if raw else fitz.Point(rect.x0, rect.y0 + rect.height * 0.8)
        return {
            "text": merged_text,
            "rect": rect,
            "origin": origin,
            "size": float(max(s.get("size", 10.0) for s in visible)),
            "color": _int_to_rgb(first.get("color", 0)),
            "font": first.get("font", ""),
            "flags": int(first.get("flags", 0)),
        }

    merged_text = "".join(s.get("text", "") for s in spans)
    stripped = merged_text.strip()
    if not stripped or not _is_translatable(stripped):
        return None

    visible = [s for s in spans if s.get("text", "").strip()]
    if not visible:
        return None
    rects = [fitz.Rect(s["bbox"]) for s in visible]
    rect = fitz.Rect(
        min(r.x0 for r in rects),
        min(r.y0 for r in rects),
        max(r.x1 for r in rects),
        max(r.y1 for r in rects),
    )
    fmt = visible[0]
    raw = fmt.get("origin")
    origin = fitz.Point(raw) if raw else fitz.Point(rect.x0, rect.y0 + rect.height * 0.8)

    sizes = [s.get("size", 10.0) for s in visible]
    dominant_size = max(set(sizes), key=sizes.count)

    bold_chars = sum(len(s.get("text", "").strip()) for s in visible if s.get("flags", 0) & 16)
    total_chars = sum(len(s.get("text", "").strip()) for s in visible)
    is_bold = bold_chars > total_chars * 0.5 if total_chars else False

    flags = fmt.get("flags", 0)
    if is_bold:
        flags = flags | 16
    else:
        flags = flags & ~16

    return {
        "text": stripped,
        "rect": rect,
        "origin": origin,
        "size": float(dominant_size),
        "color": _int_to_rgb(fmt.get("color", 0)),
        "font": fmt.get("font", ""),
        "flags": flags,
    }


def _group_lines_into_paragraphs(merged_lines: list[dict]) -> list[list[dict]]:
    """Group consecutive lines with compatible formatting into paragraphs."""
    if not merged_lines:
        return []
    groups = []
    current = [merged_lines[0]]
    for ml in merged_lines[1:]:
        prev = current[-1]
        same_size = abs(ml["size"] - prev["size"]) < 1.5
        same_x = abs(ml["rect"].x0 - current[0]["rect"].x0) < 5.0
        gap = ml["rect"].y0 - prev["rect"].y1
        consecutive = gap < prev["size"] * 0.5
        same_color = ml["color"] == prev["color"]
        if same_size and same_x and consecutive and same_color:
            current.append(ml)
        else:
            groups.append(current)
            current = [ml]
    groups.append(current)
    return groups


def _make_unit(page_no: int, group: list[dict]) -> dict:
    """Create a unit dict from a group of merged lines."""
    if len(group) == 1:
        ml = group[0]
        return {
            "type": "line",
            "page_no": page_no,
            "rect": ml["rect"],
            "origin": ml["origin"],
            "text": ml["text"],
            "size": ml["size"],
            "color": ml["color"],
            "font": ml["font"],
            "flags": ml["flags"],
            "line_rects": [ml["rect"]],
        }
    merged_text = " ".join(ml["text"] for ml in group)
    first = group[0]
    last = group[-1]
    block_rect = fitz.Rect(
        min(ml["rect"].x0 for ml in group),
        first["rect"].y0,
        max(ml["rect"].x1 for ml in group),
        last["rect"].y1,
    )
    line_height = (group[1]["origin"].y - group[0]["origin"].y) if len(group) > 1 else first["size"] * 1.3
    return {
        "type": "paragraph",
        "page_no": page_no,
        "rect": block_rect,
        "origin": first["origin"],
        "text": merged_text,
        "size": first["size"],
        "color": first["color"],
        "font": first["font"],
        "flags": first["flags"],
        "line_height": line_height,
        "line_rects": [ml["rect"] for ml in group],
        "max_lines": len(group) + 1,
    }


def _collect_text_units(doc: fitz.Document) -> list[dict]:
    """
    Collect translatable text at LINE level, with paragraph grouping.

    All spans on a line are merged into one string.  Consecutive same-format
    lines within a block are grouped into paragraphs and translated as one
    unit for full sentence context.  Single lines stay independent.

    Non-translatable lines (bullet symbols, blanks) act as paragraph breaks
    so bullet points and table cells stay independent.
    """
    units = []
    for page_no in range(doc.page_count):
        page = doc[page_no]
        page_width = page.rect.width
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            segments: list[list[dict]] = []
            current_seg: list[dict] = []
            for line in block.get("lines", []):
                ml = _merge_line(line.get("spans", []))
                if ml:
                    current_seg.append(ml)
                else:
                    if current_seg:
                        segments.append(current_seg)
                        current_seg = []
            if current_seg:
                segments.append(current_seg)

            for segment in segments:
                groups = _group_lines_into_paragraphs(segment)
                for group in groups:
                    max_w = max(ml["rect"].width for ml in group)
                    if len(group) > 1 and max_w < page_width * 0.35:
                        for ml in group:
                            units.append(_make_unit(page_no, [ml]))
                    else:
                        units.append(_make_unit(page_no, group))
    return units


def _annotate_page(page: fitz.Page, page_units: list[tuple]) -> int:
    """Add strikethrough + popup comment annotations for translated units.

    Returns the number of annotations added.
    """
    count = 0
    for unit, new_text in page_units:
        if not new_text or not str(new_text).strip():
            continue
        translation = str(new_text).strip()
        orig_text = unit["text"]
        if translation == orig_text:
            continue

        line_rects = unit.get("line_rects", [unit["rect"]])

        try:
            annot = page.add_strikeout_annot(line_rects)
            annot.set_colors(stroke=(1, 0, 0))
            annot.set_opacity(0.6)
            annot.update()
        except Exception:
            pass

        try:
            icon_x = min(unit["rect"].x1 + 2, page.rect.width - 20)
            icon_pos = fitz.Point(icon_x, unit["rect"].y0)
            note = page.add_text_annot(icon_pos, translation, icon="Comment")
            note.set_colors(stroke=(0, 0.3, 0.8))
            note.update()
            count += 1
        except Exception:
            pass

    return count


def translate_pdf(
    input_path: str,
    output_path: str,
    target_lang: str,
    backend: str = "google",
    api_key: str = "",
    progress: "TranslationProgress" = None,
    domain_context: str = "",
    telemetry: dict | None = None,
) -> str:
    if progress is None:
        progress = TranslationProgress()
    progress.reset()
    progress.set_phase("Opening PDF...")

    job_started_at = time.perf_counter()
    phrases = get_protected_phrases()
    telemetry = telemetry if telemetry is not None else {}
    telemetry.setdefault("timings", {})
    telemetry.setdefault("document", {})

    load_started_at = time.perf_counter()
    doc = fitz.open(input_path)
    telemetry["timings"]["load_pdf_seconds"] = round(time.perf_counter() - load_started_at, 3)
    telemetry["document"].update({
        "document_mode": "pdf",
        "backend": backend,
        "page_count": doc.page_count,
    })

    progress.set_phase("Collecting text from PDF...")
    collect_started_at = time.perf_counter()
    units = _collect_text_units(doc)
    telemetry["timings"]["collect_pdf_seconds"] = round(
        time.perf_counter() - collect_started_at, 3)

    all_texts = [u["text"] for u in units]
    non_empty = [t for t in all_texts if t.strip()]

    estimated_batches = (len(non_empty) + 11) // 12
    total_steps = estimated_batches + FINALIZATION_PROGRESS_STEPS
    progress.set_total(max(1, total_steps))

    telemetry["document"].update({
        "pdf_span_count": len(units),
        "pdf_translatable_count": len(non_empty),
        "estimated_total_steps": total_steps,
    })

    if not non_empty:
        progress.set_phase("No translatable text found.")
        progress.advance("Complete")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc.save(output_path)
        doc.close()
        telemetry["timings"]["total_job_seconds"] = round(
            time.perf_counter() - job_started_at, 3)
        return output_path

    progress.set_phase("Translating PDF...")
    translation_started_at = time.perf_counter()

    translated_texts = legacy_batch_translate(
        all_texts,
        target_lang,
        backend,
        api_key,
        phrases,
        progress,
        domain_context,
        telemetry=telemetry,
        skip_decimal_normalization=True,
    )

    telemetry["timings"]["translate_pdf_seconds"] = round(
        time.perf_counter() - translation_started_at, 3)

    progress.set_phase("Adding translation annotations...")
    by_page: dict[int, list] = {}
    for unit, new_text in zip(units, translated_texts):
        by_page.setdefault(unit["page_no"], []).append((unit, new_text))

    # Work on a copy of the original document (preserves everything)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    doc.close()

    out_doc = fitz.open(output_path)
    try:
        total_annotations = 0
        for page_no in range(out_doc.page_count):
            pu = by_page.get(page_no, [])
            if pu:
                total_annotations += _annotate_page(out_doc[page_no], pu)

        save_started_at = time.perf_counter()
        out_doc.saveIncr()
        telemetry["timings"]["save_pdf_seconds"] = round(
            time.perf_counter() - save_started_at, 3)
        telemetry["document"]["annotation_count"] = total_annotations
    finally:
        out_doc.close()

    telemetry["timings"]["total_job_seconds"] = round(
        time.perf_counter() - job_started_at, 3)

    progress.advance("Translation complete")
    return output_path
