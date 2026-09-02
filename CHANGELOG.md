# Changelog — AI Translator 2

## [Unreleased] — XLSX Spreadsheet Translation Support

Adds a fourth document mode ("Spreadsheet") that translates `.xlsx` Excel files — string cells, sheet names, and header/footer text — while preserving formulas, numbers, formatting, charts, images, merged cells, and all non-text elements. Based on the Legacy translation engine.

### Task Tracker

| # | Task | Status | Files |
|---|------|--------|-------|
| 1 | Add `openpyxl` dependency | Done | requirements.txt |
| 2 | Create `xlsx_translator.py` — core XLSX engine | Done | xlsx_translator.py (new) |
| 3 | Wire dispatch in `translate_document()` | Done | translator.py |
| 4 | Server accepts `.xlsx` uploads | Done | app.py |
| 5 | Frontend accepts `.xlsx` + Spreadsheet mode pill | Done | index.html, app.js |

### Added
- New document mode: **Spreadsheet** — translates string cells, sheet names, headers/footers in `.xlsx` workbooks
- New module: `xlsx_translator.py` — handles XLSX text extraction and reassembly via openpyxl
- New dependency: `openpyxl`
- Drop zone now accepts `.xlsx` alongside `.docx` and `.pptx`
- Auto-detection: `.xlsx` files force Spreadsheet mode regardless of UI selection
- Fourth mode pill in Document Mode selector

### Changed
- `/translate` endpoint accepts `.xlsx` uploads
- `/download` endpoint returns correct MIME type for `.xlsx` files
- File badge shows "Spreadsheet" for `.xlsx` files
- Telemetry popup handles Spreadsheet mode label

### Unchanged (zero regression)
- Legacy DOCX mode, General DOCX mode, Presentation PPTX mode — no code changes
- All translation backends (Google, Gemini, DeepL) — no changes

---

## [Unreleased] — PPTX Presentation Translation Support

Adds a third document mode ("Presentation") that translates `.pptx` PowerPoint files while preserving all images, layout, animations, and formatting. Based on the Legacy translation engine.

See: [presentation.md](presentation.md) (design doc), [implementation plan](.claude/plans/) (task breakdown)

### Task Tracker

| # | Task | Status | Files |
|---|------|--------|-------|
| 1 | Make `legacy_batch_translate` public + add python-pptx dep | Done | translator.py, requirements.txt |
| 2 | Create `pptx_translator.py` — core PPTX engine | Done | pptx_translator.py (new) |
| 3 | Wire dispatch in `translate_document()` | Done | translator.py |
| 4 | Server accepts `.pptx` uploads | Done | app.py |
| 5 | Frontend accepts `.pptx` files | Done | index.html, app.js |
| 6 | Presentation mode pill in UI | Done | index.html, app.js |
| 7 | Telemetry, edge cases, polish | Done | pptx_translator.py, app.js |

### Added
- New document mode: **Presentation** — translates all text fields in `.pptx` slides
- New module: `pptx_translator.py` — handles PPTX text extraction and reassembly
- New dependency: `python-pptx`
- Drop zone now accepts `.pptx` alongside `.docx`
- Auto-detection: `.pptx` files force Presentation mode regardless of UI selection
- Third mode pill in Document Mode selector

### Changed
- `_legacy_batch_translate` renamed to `legacy_batch_translate` (now public API for cross-module use)
- `_normalize_run_tags` renamed to `normalize_run_tags` (same reason)
- `/translate` endpoint accepts `.pptx` uploads
- `/download` endpoint returns correct MIME type for `.pptx` files
- Output filename preserves original extension (`.docx` or `.pptx`)

### Unchanged (zero regression)
- Legacy DOCX mode — no code changes
- General DOCX mode — no code changes
- All translation backends (Google, Gemini, DeepL) — no changes
- Settings, phrases, domain context — no changes
- Telemetry structure — extended, not modified
