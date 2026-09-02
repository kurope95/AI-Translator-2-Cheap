"""
XLSX Spreadsheet Translator
Translates all string cells and sheet names in Excel workbooks while preserving
formulas, numbers, formatting, charts, images, and all non-text elements.
Based on core/api_clients legacy_batch_translate (Legacy engine).
"""

import os
import time

import openpyxl

from core.api_clients import legacy_batch_translate
from core.config import get_protected_phrases
from core.constants import FINALIZATION_PROGRESS_STEPS
from core.progress import TranslationProgress


def _collect_text_units(wb):
    """
    Walk all sheets and collect translatable text.
    Returns a list of dicts, each with a 'text' key and a write-back reference.
    """
    units = []

    for ws in wb.worksheets:
        if ws.title and ws.title.strip():
            units.append({"type": "sheet_title", "sheet": ws, "text": ws.title})

        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "s" and cell.value and str(cell.value).strip():
                    units.append({"type": "cell", "cell": cell, "text": str(cell.value)})

        for attr in ("oddHeader", "evenHeader", "oddFooter", "evenFooter"):
            val = getattr(ws, attr, None)
            if val and isinstance(val, str) and val.strip():
                units.append({"type": "header_footer", "sheet": ws, "attr": attr, "text": val})

    return units


def _reassemble_translations(units, translated_texts):
    """Write translated text back into the original workbook objects."""
    for unit, translated in zip(units, translated_texts):
        if unit["type"] == "cell":
            unit["cell"].value = translated
        elif unit["type"] == "sheet_title":
            unit["sheet"].title = translated
        elif unit["type"] == "header_footer":
            setattr(unit["sheet"], unit["attr"], translated)


def translate_spreadsheet(
    input_path: str,
    output_path: str,
    target_lang: str,
    backend: str = "google",
    api_key: str = "",
    progress: TranslationProgress = None,
    domain_context: str = "",
    telemetry: dict | None = None,
) -> str:
    """
    Translate an .xlsx workbook while preserving all non-text elements.
    """
    if progress is None:
        progress = TranslationProgress()
    progress.reset()
    progress.set_phase("Preparing spreadsheet...")

    job_started_at = time.perf_counter()
    phrases = get_protected_phrases()
    telemetry = telemetry if telemetry is not None else {}
    telemetry.setdefault("timings", {})
    telemetry.setdefault("document", {})

    load_started_at = time.perf_counter()
    wb = openpyxl.load_workbook(input_path)
    telemetry["timings"]["load_spreadsheet_seconds"] = round(time.perf_counter() - load_started_at, 3)

    telemetry["document"].update({
        "document_mode": "spreadsheet",
        "backend": backend,
        "sheet_count": len(wb.worksheets),
    })

    progress.set_phase("Collecting text from sheets...")
    collect_started_at = time.perf_counter()
    units = _collect_text_units(wb)
    telemetry["timings"]["collect_xlsx_seconds"] = round(time.perf_counter() - collect_started_at, 3)

    texts = [u["text"] for u in units]

    estimated_batches = (len(texts) + 11) // 12
    total_steps = estimated_batches + FINALIZATION_PROGRESS_STEPS
    progress.set_total(max(1, total_steps))

    telemetry["document"].update({
        "spreadsheet_text_unit_count": len(units),
        "estimated_total_steps": total_steps,
    })

    if not texts:
        progress.set_phase("No translatable text found.")
        progress.advance("Complete")
        wb.save(output_path)
        telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)
        return output_path

    progress.set_phase("Translating spreadsheet...")
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

    telemetry["timings"]["translate_xlsx_seconds"] = round(time.perf_counter() - translation_started_at, 3)

    progress.set_phase("Reassembling spreadsheet...")
    _reassemble_translations(units, translated_texts)

    progress.set_phase("Saving spreadsheet...")
    save_started_at = time.perf_counter()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)
    telemetry["timings"]["save_spreadsheet_seconds"] = round(time.perf_counter() - save_started_at, 3)
    telemetry["timings"]["total_job_seconds"] = round(time.perf_counter() - job_started_at, 3)

    progress.advance("Translation complete")
    return output_path
