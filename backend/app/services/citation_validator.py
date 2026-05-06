from __future__ import annotations

import re


_CITATION_RE = re.compile(r"\[(\d+)\]")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?])\s+")


def extract_citation_indices(text: str) -> set[int]:
    out: set[int] = set()
    for m in _CITATION_RE.finditer(text):
        try:
            out.add(int(m.group(1)))
        except ValueError:
            continue
    return out


def _split_units(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    units: list[str] = []
    for ln in lines:
        parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(ln) if p.strip()]
        units.extend(parts or [ln])
    return units


def validate_answer_citations(answer: str, *, max_index: int) -> bool:
    """
    MVP rule (docs/TECH_DESIGN.md):
    - every fact sentence / point must include a `[n]`
    - `n` must be within retrieved chunk indices (1..max_index)
    """
    if not answer.strip():
        return False

    units = _split_units(answer)
    if not units:
        return False

    for unit in units:
        idxs = extract_citation_indices(unit)
        if not idxs:
            return False
        if any(i < 1 or i > max_index for i in idxs):
            return False
    return True


def repair_missing_citations(answer: str, *, fallback_index: int = 1) -> str:
    """
    Best-effort: append a fallback citation to any sentence/line that has no citation.
    This is *not* semantic alignment, but matches the MVP "allow one repair pass" rule.
    """
    if not answer.strip():
        return answer

    lines = answer.splitlines()
    repaired: list[str] = []
    for ln in lines:
        if not ln.strip():
            repaired.append(ln)
            continue
        if extract_citation_indices(ln):
            repaired.append(ln)
            continue
        repaired.append(f"{ln} [{fallback_index}]")
    return "\n".join(repaired)

