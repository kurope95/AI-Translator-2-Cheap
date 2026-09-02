"""
Shared paragraph run merge + <rN> tagging for DOCX and PPTX translation paths.

Callers merge adjacent runs with format-specific predicates, then call
fuse_merged_paragraph_runs() to produce the fused string sent to translators.
"""


def merge_adjacent_runs_inplace(runs: list, can_merge_into_previous) -> list:
    """
    Merge formatting-identical neighboring runs into the first run in each group.

    runs: iterable of objects with mutable .text (str).
    can_merge_into_previous(prev_run, current_run) -> bool
      If True, current_run.text is appended to prev_run.text and cleared on current.
    """
    merged = []
    for run in runs:
        if not merged:
            merged.append(run)
            continue

        prev = merged[-1]
        if can_merge_into_previous(prev, run):
            prev.text += run.text
            run.text = ""
        else:
            merged.append(run)

    return merged


def fuse_merged_paragraph_runs(merged_runs) -> tuple[list[tuple[int, object, str, str, str]], str]:
    """
    Build numbered <r idx >…</r idx > segments from merged runs.

    Indices match enumerate(merged_runs) positions (skipped empty runs preserve gaps).

    Returns:
        valid_runs: [(idx, run, leading_ws, trailing_ws, core.strip()), ...]
        fused_text: full paragraph fragment for the translator
    """
    valid_runs: list[tuple[int, object, str, str, str]] = []
    fused_para_text = ""

    for idx, run in enumerate(merged_runs):
        original = run.text
        if not original:
            continue
        if not original.strip():
            fused_para_text += original
            continue

        leading = original[: len(original) - len(original.lstrip())]
        trailing = original[len(original.rstrip()) :]
        core_text = original.strip()
        valid_runs.append((idx, run, leading, trailing, core_text))
        fused_para_text += f"{leading}<r{idx}>{core_text}</r{idx}>{trailing}"

    return valid_runs, fused_para_text
