"""
SQLite translation memory (persistent) + process-local duplicate segment reuse.

Duplicate segments reuse in-memory lookups first (Feature 7), then SQLite hits (Feature 4).
New translations from the API are written back automatically.
Disable with AI_TRANSLATOR_DISABLE_TM=1.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path

from core.config import _data_dir

_lock = threading.RLock()

# Feature 7: deduplicate identical (target_lang + source fingerprint) segments in-memory.
_SEGMENT_RAM: dict[tuple[str, str], str] = {}

DISABLE = os.environ.get("AI_TRANSLATOR_DISABLE_TM", "").strip().lower() in {"1", "true", "yes"}


def tm_stats_bucket(telemetry: dict | None) -> dict | None:
    if telemetry is None:
        return None
    bucket = telemetry.setdefault("translation_memory", {})
    for key in ("memory_hits", "sqlite_hits", "misses", "pairs_stored"):
        bucket.setdefault(key, 0)
    return bucket


def _normalize_lang(lang: str) -> str:
    return (lang or "").strip()


def hash_source(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _db_path() -> Path:
    return _data_dir() / "translation_memory.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tm_entry (
            source_hash TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            translated TEXT NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (source_hash, target_lang)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS tm_lang_idx ON tm_entry(target_lang)")
    conn.commit()
    return conn


def lookup(text: str, target_lang: str, stats: dict | None) -> str | None:
    if DISABLE or not isinstance(text, str) or not text.strip():
        return None
    lang = _normalize_lang(target_lang)
    h = hash_source(text)
    key = (lang, h)
    with _lock:
        if key in _SEGMENT_RAM:
            if stats is not None:
                stats.setdefault("memory_hits", 0)
                stats["memory_hits"] += 1
            return _SEGMENT_RAM[key]
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT translated FROM tm_entry WHERE source_hash=? AND target_lang=?",
                (h, lang),
            ).fetchone()
        finally:
            conn.close()
        if row:
            _SEGMENT_RAM[key] = row[0]
            if stats is not None:
                stats.setdefault("sqlite_hits", 0)
                stats["sqlite_hits"] += 1
            return row[0]

    if stats is not None:
        stats.setdefault("misses", 0)
        stats["misses"] += 1
    return None


def remember(text: str, translated: str, target_lang: str, stats: dict | None) -> None:
    if DISABLE or not isinstance(text, str) or not text.strip():
        return
    lang = _normalize_lang(target_lang)
    if not translated or not lang:
        return
    h = hash_source(text)
    key = (lang, h)
    with _lock:
        _SEGMENT_RAM[key] = translated
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO tm_entry(source_hash, target_lang, translated, updated_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(source_hash, target_lang) DO UPDATE SET
                     translated=excluded.translated,
                     updated_at=excluded.updated_at""",
                (h, lang, translated, time.time()),
            )
            conn.commit()
        finally:
            conn.close()
    if stats is not None:
        stats.setdefault("pairs_stored", 0)
        stats["pairs_stored"] += 1


def translate_with_memory(
    texts: list[str],
    target_lang: str,
    stats: dict | None,
    translate_fn: Callable[[list[str], list[str] | None], list[str]],
    progress=None,
    contexts: list[str] | None = None,
):
    """Fill hits from RAM/SQLite, translate remaining via translate_fn(novel[, novel_ctx])."""
    if DISABLE:
        return translate_fn(texts, contexts)

    lang = _normalize_lang(target_lang)
    if not lang:
        return translate_fn(texts, contexts)

    out = list(texts)
    order_keys: list[str] = []
    by_text: dict[str, list[int]] = {}
    ctx_for_text_first: dict[str, str] = {}

    for i, t in enumerate(texts):
        if not isinstance(t, str) or not t.strip():
            continue
        if t not in by_text:
            by_text[t] = []
            order_keys.append(t)
            if contexts is not None and i < len(contexts):
                ctx_for_text_first[t] = (contexts[i] or "").strip()
            elif contexts is not None:
                ctx_for_text_first[t] = ""
        by_text[t].append(i)

    novel: list[str] = []

    for tx in order_keys:
        hit = lookup(tx, lang, stats)
        if hit is not None:
            for idx in by_text[tx]:
                out[idx] = hit
        else:
            novel.append(tx)

    if not novel:
        if progress:
            progress.set_total(1)
            progress.advance("Loaded from translation memory")
        return out

    second_arg = None if contexts is None else [ctx_for_text_first.get(tx, "") for tx in novel]

    translated_novel = translate_fn(novel, second_arg)

    if not isinstance(translated_novel, list) or len(translated_novel) != len(novel):
        raise RuntimeError("Translation backend returned unexpected batch size.")

    for tx, pis, tout in zip(novel, (by_text[t] for t in novel), translated_novel):
        for ii in pis:
            out[ii] = tout
        remember(tx, tout, lang, stats)

    return out


def import_tm_pairs(rows: list[tuple[str, str]], target_lang: str) -> int:
    lang = _normalize_lang(target_lang)
    if not lang:
        return 0
    now = time.time()
    pairs = [(src.strip(), tr.strip()) for src, tr in rows if src and tr and src.strip() and tr.strip()]
    if not pairs:
        return 0

    batch_rows = []
    for src, tr in pairs:
        h = hash_source(src)
        batch_rows.append((h, lang, tr, now))
        key = (lang, h)
        _SEGMENT_RAM[key] = tr

    with _lock:
        conn = _connect()
        try:
            conn.executemany(
                """INSERT INTO tm_entry(source_hash, target_lang, translated, updated_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(source_hash, target_lang) DO UPDATE SET
                     translated=excluded.translated,
                     updated_at=excluded.updated_at""",
                batch_rows,
            )
            conn.commit()
        finally:
            conn.close()

    return len(batch_rows)


def merge_protected_phrases(existing: list[str], extra: list[str]) -> tuple[list[str], int]:
    merged: list[str] = []
    seen_lower: set[str] = set()
    for phrase in existing:
        if not isinstance(phrase, str):
            continue
        ps = phrase.strip()
        if not ps:
            continue
        k = ps.lower()
        if k in seen_lower:
            continue
        seen_lower.add(k)
        merged.append(ps)
    added = 0
    for phrase in extra:
        if not isinstance(phrase, str):
            continue
        ps = phrase.strip()
        if not ps:
            continue
        k = ps.lower()
        if k in seen_lower:
            continue
        seen_lower.add(k)
        merged.append(ps)
        added += 1
    return merged, added


def parse_protected_csv(data: bytes) -> list[str]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    phrases: list[str] = []
    if not rows:
        return phrases
    first_cells = [(c or "").strip().lower() for c in rows[0]]
    start = 0
    phrase_col = 0
    if first_cells and first_cells[0] in {"phrase", "term", "protected", "do not translate"}:
        start = 1
        phrase_col = 0
        for i, cell in enumerate(first_cells):
            if cell in {"phrase", "term", "protected", "source"}:
                phrase_col = i
                break
    for row in rows[start:]:
        if not row:
            continue
        if phrase_col >= len(row):
            continue
        p = row[phrase_col].strip()
        if p:
            phrases.append(p)
    return phrases


def parse_tm_csv(data: bytes) -> tuple[list[tuple[str, str]], bool]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    pairs: list[tuple[str, str]] = []
    if not rows:
        return [], False

    lowered = [(c or "").strip().lower() for c in rows[0]]

    synonyms_s = {"source", "english", "en", "original", "from", "phrase"}
    synonyms_t = {"target", "translation", "translated", "to", "foreign"}

    def find_col(cands):
        for i, h in enumerate(lowered):
            if h in cands:
                return i
        return None

    start = 0
    sci = None
    tci = None
    if lowered and lowered[0] in synonyms_s.union({"phrase"}):
        sci = find_col(synonyms_s) or find_col({"phrase"})
        tci = find_col(synonyms_t)
        if sci is None:
            sci = 0
        if tci is None and len(lowered) > 1:
            tci = 1 if sci == 0 else 0
        start = 1
    elif len(rows[0]) >= 2:
        sci, tci = 0, 1

    if sci is None or tci is None:
        sci, tci = 0, 1 if len(rows[0]) > 1 else 0

    for row in rows[start:]:
        if len(row) <= max(sci, tci):
            continue
        s = row[sci].strip()
        tt = row[tci].strip() if tci < len(row) else ""
        if s and tt:
            pairs.append((s, tt))

    return pairs, True
