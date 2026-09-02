# AI Translator 2 (Cheap)

A local web app that translates whole documents — **.docx, .pptx, .xlsx, .pdf,
.md, .html** — while preserving their formatting, using your own API keys
(Google Gemini, DeepL) or free Google Translate. Runs entirely on your machine;
your documents and keys never leave it except for the translation API calls you
configure.

Features: batch uploads, live progress (SSE), a persistent translation memory
(SQLite) that avoids re-paying for repeated sentences, protected phrases,
domain contexts, per-run cost telemetry, and a choice of Gemini models
(2.5 Flash/Pro, 3.0 Flash, 3.5 Flash Lite, 3.7 Flash, 3.1 Pro).

## Run it

```
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5030>. On Windows you can double-click
`launcher.vbs` (silent) or `AI Translator 2 Codex Cheap.bat` (console).

## API keys

**No keys ship with this repository and none are required to start it.**
Enter your own Gemini and/or DeepL key in the app's Settings; they are stored
locally in `config.json`, which is gitignored — never commit it. Google
Translate works without any key.
