"""
AI Translator — Flask Web Server
Upload/download endpoints, SSE progress streaming, and phrase management API.
"""

import os
import uuid
import shutil
import threading
import time
import json
import sys
import zipfile
import io
from pathlib import Path

from flask import Flask, render_template, request, send_file, jsonify, Response, stream_with_context

from translator import (
    translate_document, LANGUAGES, LANGUAGE_CODES,
    get_api_key, set_api_key,
    get_deepl_api_key, set_deepl_api_key,
    get_protected_phrases, set_protected_phrases,
    get_domain_context, get_domain_contexts, set_domain_contexts,
    TranslationProgress,
)

APP_NAME = "AI Translator 2"
HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_TRANSLATOR_PORT", "5030"))


def _is_packaged_app() -> bool:
    return getattr(sys, "frozen", False) or Path(sys.argv[0]).suffix.lower() == ".exe"


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def _data_dir() -> Path:
    if _is_packaged_app():
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        data_dir = local_appdata / APP_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).parent


BUNDLE_DIR = _bundle_dir()
DATA_DIR = _data_dir()

app = Flask(
    __name__,
    template_folder=str(BUNDLE_DIR / "templates"),
    static_folder=str(BUNDLE_DIR / "static"),
)

UPLOAD_FOLDER = DATA_DIR / "temp"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({"error": "File too large. Maximum upload size is 500 MB."}), 413


# ─── In-memory job tracking ──────────────────────────────────

jobs = {}  # job_id -> { "progress": TranslationProgress, "status": str, "output_path": str, "output_name": str, "error": str }


def _index_context():
    return dict(
        languages=LANGUAGES,
        language_codes=LANGUAGE_CODES,
        has_gemini_key=bool(get_api_key()),
        has_deepl_key=bool(get_deepl_api_key()),
        phrases=get_protected_phrases(),
        domain_context=get_domain_context(),
        domain_contexts=get_domain_contexts(),
    )


@app.route("/")
def index():
    return render_template("index.html", **_index_context())


@app.route("/v2")
def index_v2():
    return render_template("index_v2.html", **_index_context())


# ─── API Key ─────────────────────────────────────────────────

@app.route("/api/save-key", methods=["POST"])
def save_key():
    data = request.get_json()
    provider = data.get("provider", "gemini").strip().lower()
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"error": "API key cannot be empty"}), 400
    if provider == "gemini":
        set_api_key(key)
        return jsonify({"success": True, "message": "Gemini API key saved!"})
    if provider == "deepl":
        set_deepl_api_key(key)
        return jsonify({"success": True, "message": "DeepL API key saved!"})
    return jsonify({"error": f"Unsupported provider: {provider}"}), 400


@app.route("/api/check-key")
def check_key():
    return jsonify({
        "has_key": bool(get_api_key()),
        "has_gemini_key": bool(get_api_key()),
        "has_deepl_key": bool(get_deepl_api_key()),
    })


# ─── Protected Phrases ───────────────────────────────────────

@app.route("/api/phrases", methods=["GET"])
def get_phrases():
    return jsonify({"phrases": get_protected_phrases()})


@app.route("/api/phrases", methods=["POST"])
def save_phrases():
    data = request.get_json()
    phrases = data.get("phrases", [])
    set_protected_phrases(phrases)
    return jsonify({"success": True, "phrases": get_protected_phrases()})


@app.route("/api/glossary/import-csv", methods=["POST"])
def import_glossary_csv():
    """CSV import for protected phrases (one column) or translation memory pairs (two columns)."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    up = request.files["file"]
    if not up.filename:
        return jsonify({"error": "No file selected"}), 400
    raw = up.read()
    if len(raw) > 50 * 1024 * 1024:
        return jsonify({"error": "CSV file exceeds 50 MB limit."}), 413

    from core.translation_memory import (
        import_tm_pairs,
        merge_protected_phrases,
        parse_protected_csv,
        parse_tm_csv,
    )

    kind = request.form.get("kind", "protected").strip().lower()

    if kind == "protected":
        extra = parse_protected_csv(raw)
        merged, added = merge_protected_phrases(get_protected_phrases(), extra)
        set_protected_phrases(merged)
        return jsonify({
            "success": True,
            "kind": "protected",
            "rows_read": len(extra),
            "new_phrases_merged_in": added,
            "total_phrases": len(merged),
        })

    if kind == "tm":
        target_lang = request.form.get("target_lang", "").strip()
        if target_lang not in LANGUAGES:
            return jsonify({"error": f"Unsupported language for translation memory: {target_lang}"}), 400
        pairs, _detected = parse_tm_csv(raw)
        if not pairs:
            return jsonify({"error": "No valid source/target pairs found in CSV (need at least two columns)."}), 400
        n = import_tm_pairs(pairs, target_lang)
        return jsonify({"success": True, "kind": "tm", "pairs_imported": n, "target_lang": target_lang})

    return jsonify({"error": "Invalid kind; use protected or tm."}), 400


# ─── Domain Context ──────────────────────────────────────────

@app.route("/api/domain", methods=["GET"])
def get_domain():
    return jsonify({
        "domain_context": get_domain_context(),
        "domain_contexts": get_domain_contexts(),
    })


@app.route("/api/domain", methods=["POST"])
def save_domain():
    data = request.get_json()
    domain_contexts = data.get("domain_contexts")
    if domain_contexts is None:
        domain = data.get("domain_context", "")
        domain_contexts = [domain] if isinstance(domain, str) and domain.strip() else []
    set_domain_contexts(domain_contexts)
    return jsonify({
        "success": True,
        "domain_context": get_domain_context(),
        "domain_contexts": get_domain_contexts(),
    })


# ─── Translation (async with progress) ──────────────────────

@app.route("/translate", methods=["POST"])
def translate():
    """Start a translation job and return a job_id for progress tracking."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in (".docx", ".pptx", ".xlsx", ".pdf", ".md", ".markdown", ".html", ".htm"):
        return jsonify({"error": "Only .docx, .pptx, .xlsx, .pdf, .md, .html files are supported"}), 400

    language = request.form.get("language", "").strip()
    if language not in LANGUAGES:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    backend = request.form.get("backend", "google").strip()
    backend = {
        # Old ids from saved presets / bookmarked flows resolve to the current
        # lightweight model (3.1 Flash Lite retired 2026-09-02).
        "gemini-31-flash-image": "gemini-35-flash-lite",
        "gemini-31-flash-lite-preview": "gemini-35-flash-lite",
    }.get(backend, backend)
    if backend not in (
        "google",
        "gemini",
        "gemini-pro",
        "gemini-25-flash",
        "gemini-25-pro",
        "gemini-35-flash-lite",
        "gemini-37-flash",
        "deepl",
    ):
        backend = "google"

    print(f"\n[DEBUG] Job Starting: API Backend={backend}, Language={language}\n")

    api_key = ""
    if backend in ("gemini", "gemini-pro", "gemini-25-flash", "gemini-25-pro", "gemini-35-flash-lite", "gemini-37-flash"):
        api_key = get_api_key()
        if not api_key:
            return jsonify({"error": "Gemini API key not set. Please enter your key in Settings."}), 400
    elif backend == "deepl":
        api_key = get_deepl_api_key()
        if not api_key:
            return jsonify({"error": "DeepL API key not set. Please enter your key in Settings."}), 400

    domain_context = get_domain_context()
    document_mode = request.form.get("document_mode", "general").strip().lower()
    if file_ext == ".pptx":
        document_mode = "presentation"
    elif file_ext == ".xlsx":
        document_mode = "spreadsheet"
    elif file_ext == ".pdf":
        document_mode = "pdf"
    elif document_mode not in ("legacy", "general", "markdown", "html"):
        document_mode = "general"

    if file_ext in (".md", ".markdown"):
        if document_mode != "markdown":
            return jsonify({
                "error": 'Markdown files require the Markdown document mode. Select "Markdown" in the translator options.',
            }), 400
    elif file_ext in (".html", ".htm"):
        if document_mode != "html":
            return jsonify({
                "error": 'HTML files require the HTML document mode. Select "HTML" in the translator options.',
            }), 400
    elif file_ext == ".docx":
        if document_mode not in ("legacy", "general"):
            return jsonify({
                "error": "Word (.docx) files support General or Legacy mode only.",
            }), 400

    if document_mode == "markdown" and file_ext not in (".md", ".markdown"):
        return jsonify({"error": "Markdown mode applies only to .md files."}), 400
    if document_mode == "html" and file_ext not in (".html", ".htm"):
        return jsonify({"error": "HTML mode applies only to .html files."}), 400

    # Temperature: only accepted for general mode with a Gemini backend.
    # If not provided or invalid, stays None (backend uses its own default).
    temperature = None
    temp_raw = request.form.get("temperature", "").strip()
    if temp_raw:
        try:
            t = float(temp_raw)
            if 0.0 <= t <= 2.0:
                temperature = round(t, 2)
        except ValueError:
            pass
    _gemini_backends = (
        "gemini",
        "gemini-pro",
        "gemini-25-flash",
        "gemini-25-pro",
        "gemini-35-flash-lite",
        "gemini-37-flash",
    )
    if document_mode != "general" or backend not in _gemini_backends:
        temperature = None
    # Create job
    job_id = str(uuid.uuid4())
    session_dir = UPLOAD_FOLDER / job_id
    session_dir.mkdir(parents=True, exist_ok=True)

    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(file.filename)
    if not safe_filename or not Path(safe_filename).stem:
        safe_filename = "document" + file_ext

    original_name = Path(safe_filename).stem
    input_path = session_dir / f"original_{safe_filename}"
    
    # Save safely
    file.save(str(input_path))

    lang_suffix = LANGUAGE_CODES[language]
    output_filename = f"{original_name}_{lang_suffix}{file_ext}"
    output_path = session_dir / output_filename

    progress = TranslationProgress()
    jobs[job_id] = {
        "progress": progress,
        "status": "running",
        "output_path": str(output_path),
        "output_name": output_filename,
        "language": language,
        "language_code": lang_suffix,
        "backend": backend,
        "document_mode": document_mode,
        "telemetry": {},
        "error": "",
    }

    # Run translation in background thread
    def run_translation():
        try:
            telemetry = {}
            jobs[job_id]["telemetry"] = telemetry
            translate_document(
                str(input_path), str(output_path), language,
                backend=backend, api_key=api_key, progress=progress,
                domain_context=domain_context,
                document_mode=document_mode,
                telemetry=telemetry,
                temperature=temperature,
            )
            jobs[job_id]["status"] = "done"
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            print(f"\\n[BACKGROUND THREAD ERROR]\\n{tb_str}\\n")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"{type(e).__name__}: {str(e)}\\n\\n{tb_str}"

    thread = threading.Thread(target=run_translation, daemon=True)
    thread.start()

    return jsonify({
        "job_id": job_id,
        "output_name": output_filename,
        "language": language,
        "language_code": lang_suffix,
        "backend": backend,
        "document_mode": document_mode,
    })


@app.route("/api/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    """Cancel a running translation job."""
    if job_id in jobs:
        jobs[job_id]["progress"].is_cancelled = True
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Translation cancelled by user"
    return jsonify({"success": True})


@app.route("/progress/<job_id>")
def progress(job_id):
    """SSE endpoint for real-time translation progress."""
    def generate():
        if job_id not in jobs:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        while True:
            job = jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            prog = job["progress"]
            data = {
                "status": job["status"],
                "telemetry": job.get("telemetry", {}),
                **prog.to_dict(),
            }

            if job["status"] == "error":
                data["error"] = job["error"]
                yield f"data: {json.dumps(data)}\n\n"
                return

            if job["status"] == "done":
                data["percent"] = 100
                # Include full telemetry when job is done
                data["telemetry"] = job.get("telemetry", {})
                yield f"data: {json.dumps(data)}\n\n"
                return

            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/progress/<job_id>")
def progress_json(job_id):
    """JSON progress endpoint for polling fallback."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    prog = job["progress"]
    data = {
        "status": job["status"],
        "output_name": job.get("output_name", ""),
        "language": job.get("language", ""),
        "language_code": job.get("language_code", ""),
        "backend": job.get("backend", ""),
        "telemetry": job.get("telemetry", {}),
        **prog.to_dict(),
    }
    if job["status"] == "error":
        data["error"] = job["error"]
    if job["status"] == "done":
        data["percent"] = 100
    return jsonify(data)


@app.route("/api/telemetry/<job_id>")
def telemetry_json(job_id):
    """Detailed per-job telemetry for cost/performance analysis."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job.get("status", ""),
        "backend": job.get("backend", ""),
        "language": job.get("language", ""),
        "output_name": job.get("output_name", ""),
        "telemetry": job.get("telemetry", {}),
    })


@app.route("/api/download-zip", methods=["POST"])
def download_zip():
    """Download multiple completed translations as a single ZIP file."""
    data = request.get_json()
    job_ids = data.get("job_ids", [])
    if not job_ids:
        return jsonify({"error": "No job IDs provided"}), 400

    mem_zip = io.BytesIO()
    added = 0
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for jid in job_ids:
            job = jobs.get(jid)
            if not job or job.get("status") != "done":
                continue
            output_path = job.get("output_path", "")
            if output_path and os.path.exists(output_path):
                arcname = job.get("output_name", os.path.basename(output_path))
                zf.write(output_path, arcname)
                added += 1

    if added == 0:
        return jsonify({"error": "No completed translations found for the given job IDs"}), 404

    mem_zip.seek(0)
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="translations.zip",
    )


@app.route("/download/<job_id>")
def download(job_id):
    """Download the translated document after job completes."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Translation not complete"}), 400

    output_lower = job["output_name"].lower()
    if output_lower.endswith(".pptx"):
        mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif output_lower.endswith(".xlsx"):
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif output_lower.endswith(".pdf"):
        mime = "application/pdf"
    elif output_lower.endswith((".md", ".markdown")):
        mime = "text/markdown"
    elif output_lower.endswith((".html", ".htm")):
        mime = "text/html"
    else:
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return send_file(
        job["output_path"],
        as_attachment=True,
        download_name=job["output_name"],
        mimetype=mime,
    )


def _cleanup_old_sessions(exclude: str = None):
    if not UPLOAD_FOLDER.exists():
        return
    for item in UPLOAD_FOLDER.iterdir():
        if item.is_dir() and item.name != exclude:
            try:
                shutil.rmtree(item)
            except Exception:
                pass


def run_server():
    _cleanup_old_sessions()
    print("\n" + "=" * 60)
    print("   AI Translator is running!")
    print(f"   Open your browser at: http://localhost:{PORT}")
    print("=" * 60 + "\n")
    app.run(debug=False, host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    run_server()
