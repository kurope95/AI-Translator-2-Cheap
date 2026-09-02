# PPTX Presentation Translation — Implementation Plan

## Goal

Add a third document mode — **Presentation** — to AI Translator 2. The user drops in a `.pptx` file (or a Google Slides export saved as `.pptx`), picks languages and a backend exactly like today, and gets back a `.pptx` with all text fields translated while **images, layout, shapes, animations, transitions, charts, SmartArt, master slides, and every other non-text element remain byte-for-byte identical**.

Translation logic is based on **Legacy mode** — fast, reliable, no context-building overhead.

---

## Core Principles

1. **Zero regression** — Legacy and General DOCX modes must not be touched. All PPTX logic lives in its own module and a clean new code path.
2. **Format-in, format-out** — Input `.pptx`, output `.pptx`. No intermediate conversions.
3. **Text only** — We translate text inside shapes, tables, text boxes, titles, subtitles, group shapes, and speaker notes. We do **not** touch text baked into images, charts data labels, or embedded OLE objects.
4. **Preserve everything else** — The `python-pptx` library operates on the underlying XML. We only mutate `<a:r>` (run) text nodes. Fonts, sizes, colors, bold/italic, bullet styles, alignment, placeholders, slide masters, layouts, images, media — all untouched.
5. **Reuse the translation engine** — The same `_legacy_batch_translate()` function used by DOCX Legacy mode handles all API calls, phrase protection, batching, retries, and telemetry.

---

## Architecture Overview

```
User drops .pptx
       |
       v
app.py  ──>  /translate  (accepts .pptx OR .docx)
       |
       v
translate_document()          # existing entry point
   |-- document_mode == "legacy"       -> DOCX legacy path (unchanged)
   |-- document_mode == "general"      -> DOCX general path (unchanged)
   |-- document_mode == "presentation" -> NEW: pptx_translator.translate_presentation()
       |
       v
pptx_translator.py  (new file)
   1. Load .pptx via python-pptx
   2. Walk all slides + notes + masters -> collect text runs
   3. Fuse runs with <r0>...</r0> tags (same as Legacy)
   4. Call _legacy_batch_translate() from translator.py
   5. Parse translated text back into runs
   6. Save .pptx
```

---

## File-by-File Changes

### 1. `pptx_translator.py` (NEW — ~250-350 lines)

The entire PPTX extraction/reassembly layer. Kept in a single new file to avoid polluting `translator.py`.

#### Key functions:

```
translate_presentation(
    input_path, output_path, target_lang,
    backend, api_key, progress, domain_context,
    telemetry
) -> str
```

**Step 1 — Load**
- `from pptx import Presentation`
- `prs = Presentation(input_path)`

**Step 2 — Collect text units**
- Walk every slide in `prs.slides`
- For each slide, walk shapes recursively via `_collect_shapes(slide.shapes)`
- Recursive walker handles:
  - **Regular shapes** with `.text_frame` — iterate `.paragraphs` -> `.runs`
  - **Table shapes** (`shape.has_table`) — iterate `table.rows` -> `cells` -> `text_frame.paragraphs` -> `runs`
  - **Group shapes** (`shape.shape_type == MSO_SHAPE_TYPE.GROUP`) — recurse into `shape.shapes`
  - **Placeholders** (titles, subtitles, body) — these are regular shapes with a text_frame, handled by the same path
- Optionally walk `slide.notes_slide.notes_text_frame` for speaker notes
- Walk slide masters and layouts only if they contain unique text (configurable, default: skip — masters are usually template text the user doesn't want translated)

**Data structure collected:**
```python
TextUnit = {
    "paragraph": paragraph_obj,   # python-pptx Paragraph
    "valid_runs": [(idx, run, leading, trailing, core_text), ...],
    "fused_text": "<r0>Title text</r0> <r1>more text</r1>"
}
```

This mirrors the Legacy DOCX approach exactly — fuse runs with `<rN>` XML markers, translate the fused string, parse markers back out, write into runs.

**Step 3 — Translate**
- Collect all `fused_text` strings into a flat list
- Call `_legacy_batch_translate()` (imported from `translator.py`)
- This reuses all existing batching, retries, phrase protection, backend routing (Google/Gemini/DeepL), and telemetry

**Step 4 — Reassemble**
- Identical logic to `_legacy_translate_paragraphs()` reassembly:
  - Parse `<rN>` tags from translated output
  - If all tags preserved: write each run's text back individually (formatting preserved perfectly)
  - If tags lost: fallback — put all text in first run, clear remaining runs
- RTL handling for Arabic (same as DOCX)

**Step 5 — Save**
- `prs.save(output_path)` — python-pptx writes only modified XML parts, everything else passes through unchanged

#### Recursive shape walker:

```python
def _collect_shapes(shapes) -> list[shape]:
    """Recursively collect all shapes, descending into groups."""
    result = []
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            result.extend(_collect_shapes(shape.shapes))
        else:
            result.append(shape)
    return result
```

#### Run fusion (reused from Legacy):

The same `<r0>text</r0>` approach. For each paragraph in a text frame:
1. Merge adjacent runs with identical formatting (reduce noise)
2. Tag each content-bearing run: `<r0>Hello</r0> <r1>World</r1>`
3. Send the fused string for translation
4. Parse tags back and write into the original run objects

This means **bold, italic, font size, color, hyperlinks** on individual runs are preserved — we only replace `.text`, never touch formatting properties.

---

### 2. `translator.py` — Minimal changes

**What changes:**
- `translate_document()` gains a third branch: `if document_mode == "presentation":`
  - Imports and calls `pptx_translator.translate_presentation()`
  - Passes through all standard args (target_lang, backend, api_key, progress, domain_context, telemetry)
- The valid mode check expands: `{"legacy", "general"}` -> `{"legacy", "general", "presentation"}`

**What does NOT change:**
- `_legacy_batch_translate()` — called as-is by the PPTX module
- `_legacy_translate_paragraphs()` — stays DOCX-only, untouched
- All General mode code — untouched
- All helper functions — untouched

---

### 3. `app.py` — Upload and download changes

**Upload validation (`/translate` route):**
```python
# BEFORE:
if not file.filename.lower().endswith(".docx"):
    return jsonify({"error": "Only .docx files are supported"}), 400

# AFTER:
ext = Path(file.filename).suffix.lower()
if ext not in (".docx", ".pptx"):
    return jsonify({"error": "Only .docx and .pptx files are supported"}), 400
```

**Auto-detect mode from file type:**
- If the uploaded file is `.pptx`, force `document_mode = "presentation"` regardless of what the UI sent
- If `.docx`, use whatever mode the user selected (legacy/general) — unchanged behavior

**Output filename:**
- DOCX: `{original_name}_{lang_code}.docx` (unchanged)
- PPTX: `{original_name}_{lang_code}.pptx`

**Download MIME type:**
- Detect from file extension and return the correct MIME type
- `.pptx`: `application/vnd.openxmlformats-officedocument.presentationml.presentation`

**Document mode validation expands:**
```python
if document_mode not in ("legacy", "general", "presentation"):
    document_mode = "general"
```

---

### 4. `templates/index.html` — UI changes

**Document Mode pills — add "Presentation":**
```html
<!-- Existing (unchanged): -->
<label class="engine-pill engine-pill-service">
    <input type="radio" name="document-mode" value="legacy" id="radio-mode-legacy">
    <span class="pill-body">Legacy</span>
</label>
<label class="engine-pill">
    <input type="radio" name="document-mode" value="general" id="radio-mode-general" checked>
    <span class="pill-body">General</span>
</label>

<!-- NEW: -->
<label class="engine-pill engine-pill-presentation">
    <input type="radio" name="document-mode" value="presentation" id="radio-mode-presentation">
    <span class="pill-body">Presentation</span>
</label>
```

**Mode description update:**
- When "Presentation" is selected, the description area shows: *"Translates all text in PowerPoint slides while preserving layout, images, and formatting. Based on the Legacy translation engine."*

**Drop zone text update:**
```html
<!-- BEFORE: -->
<p class="drop-text">Drag & drop your <strong>.docx</strong> files here</p>

<!-- AFTER: -->
<p class="drop-text">Drag & drop your <strong>.docx</strong> or <strong>.pptx</strong> files here</p>
```

**File input accept attribute:**
```html
<!-- BEFORE: -->
<input type="file" id="file-input" accept=".docx" multiple hidden>

<!-- AFTER: -->
<input type="file" id="file-input" accept=".docx,.pptx" multiple hidden>
```

---

### 5. `static/app.js` — Frontend logic

**File validation in `addFiles()`:**
```javascript
// BEFORE:
if (!file.name.toLowerCase().endsWith(".docx")) return;

// AFTER:
const ext = file.name.toLowerCase();
if (!ext.endsWith(".docx") && !ext.endsWith(".pptx")) return;
```

**Auto-select Presentation mode:**
- When a `.pptx` file is added and no `.docx` files are in the queue, auto-switch to Presentation mode
- When a `.docx` file is added and mode is Presentation, switch back to General
- If the queue is mixed (both `.docx` and `.pptx`), show a warning toast: *"Mixed file types detected. DOCX files will use the selected document mode, PPTX files will always use Presentation mode."*
- The backend overrides `document_mode` per-file anyway (`.pptx` always forces `"presentation"` server-side), so this is just a UX hint

**Mode label formatting:**
```javascript
function formatModeLabel(mode) {
    if (mode === "legacy") return "Legacy";
    if (mode === "presentation") return "Presentation";
    return "General";
}
```

**File tile badges:**
- PPTX files show a "PPTX" badge on their tile instead of just the mode badge
- Gives visual distinction in the queue

**Temperature panel:**
- Disabled for Presentation mode (same as Legacy — we use the same engine)

**Summary chip in shelf header:**
- Shows "Presentation" when that mode is active

**Engine detail description when Presentation selected:**
- Show: *"Presentation mode — translates all text fields in .pptx slides. Images and layout preserved."*

---

### 6. `requirements.txt`

Add one dependency:
```
python-pptx
```

---

### 7. `static/style.css` — Minimal styling

- Style for the `.engine-pill-presentation` label (optional — can use existing pill styles)
- PPTX file badge color (e.g., orange/coral to distinguish from DOCX blue)

---

## What Gets Translated

| Element | Translated? | How |
|---|---|---|
| Shape text (titles, subtitles, body text) | Yes | text_frame.paragraphs.runs |
| Table cell text | Yes | table.cell.text_frame.paragraphs.runs |
| Text in grouped shapes | Yes | Recursive descent into group |
| Speaker notes | Yes (configurable) | notes_slide.notes_text_frame |
| Text in SmartArt | Partial — accessible text only | Shapes that python-pptx exposes |
| Chart titles / axis labels | No | python-pptx chart API is read-only for labels |
| Text baked into images | No | Not accessible — it's pixels |
| Slide master / layout text | No (by default) | Usually template boilerplate |
| Embedded OLE objects | No | Opaque binary blobs |
| Hyperlinks | Preserved, not translated | Run-level property, text changes don't affect it |
| Comments | No | Not commonly needed |

---

## Implementation Order

### Phase 1 — Core PPTX engine (can test standalone)
1. Create `pptx_translator.py` with `translate_presentation()`
2. Implement shape walker, run fusion, reassembly
3. Add `python-pptx` to `requirements.txt`
4. Write a quick CLI test: `python -c "from pptx_translator import translate_presentation; translate_presentation('test.pptx', 'out.pptx', 'German', 'google', '', ...)"`

### Phase 2 — Wire into backend
5. Update `translator.py` — add presentation branch in `translate_document()`
6. Update `app.py` — accept `.pptx` uploads, auto-detect mode, correct MIME types

### Phase 3 — UI
7. Add Presentation pill to `index.html`
8. Update `app.js` — file validation, auto-mode switching, labels
9. Update drop zone text and file input accept
10. Minor CSS for presentation pill/badge

### Phase 4 — Test with real files
11. Test with a simple 5-slide presentation
12. Test with the user's 40-page feature-rich presentation
13. Verify: images intact, layout intact, animations intact, only text changed
14. Test mixed queue (DOCX + PPTX in same batch)
15. Test all backends (Google Translate, Gemini, DeepL)

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| python-pptx doesn't expose text in some shape types | Medium | Recursive walker + fallback to XML iteration for edge cases |
| Grouped shapes with deep nesting | Low | Recursive walker handles arbitrary depth |
| SmartArt text not accessible | Medium | python-pptx has limited SmartArt support — document as known limitation |
| Large presentations (40+ slides) hit API rate limits | Low | Already handled by existing batching/retry logic in `_legacy_batch_translate()` |
| Run tag loss during translation | Low | Already handled by fallback reassembly logic (same as DOCX Legacy) |
| Google Slides export has non-standard XML | Low | python-pptx handles standard OOXML; Google exports valid .pptx |

---

## Estimated Effort

| Phase | Time |
|---|---|
| Phase 1 — Core PPTX engine | ~2-3 hours |
| Phase 2 — Backend wiring | ~30 minutes |
| Phase 3 — UI changes | ~1 hour |
| Phase 4 — Testing & fixes | ~1-2 hours |
| **Total** | **~5-7 hours** |

---

## What This Plan Does NOT Include

- `.odp` (LibreOffice Impress) support — different format entirely
- Chart data label translation — python-pptx chart API limitation
- Image OCR — out of scope, would require a vision model
- Slide master/layout translation — skipped by default to avoid corrupting templates
- Any changes to DOCX Legacy or General mode — zero regression guaranteed
