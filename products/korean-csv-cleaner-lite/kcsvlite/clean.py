"""Turning a raw grid into a table: header, blanks, text, duplicates.

Every step reports what it changed through a :class:`ChangeLog`, so the output
file is never the only evidence of what happened to the data.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

# Zero-width space, ZWNJ, ZWJ, word joiner, BOM, soft hyphen, LRM, RLM.
INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad\u200e\u200f"), None)
# Non-breaking and ideographic spaces look like a space and are not one.
SPACES = {"\u00a0": " ", "\u3000": " ", "\t": " "}

_NUMBER = re.compile(r"^[-+]?[\d,]*\.?\d+$")
_DATE = re.compile(r"^\d{2,4}[-./년]\s?\d{1,2}[-./월]\s?\d{1,2}")


def is_blank(value: object) -> bool:
    """True for None and for whitespace-only strings.

    ``csv`` gives ``""`` for a missing cell, but a value pasted from Excel can
    arrive as a lone non-breaking space and pass a naive ``if value`` test.
    """
    if value is None:
        return True
    return str(value).replace("\u00a0", " ").replace("\u3000", " ").strip() == ""


def clean_text(value: object, nfkc: bool = True) -> str:
    """Invisible characters out, full-width in, whitespace collapsed."""
    if is_blank(value):
        return ""
    text = str(value).translate(INVISIBLE)
    for bad, good in SPACES.items():
        text = text.replace(bad, good)
    if nfkc:
        text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def looks_numeric(value: str) -> bool:
    """A number, or a date, rather than a label. Used only for header scoring."""
    text = clean_text(value)
    if not text:
        return False
    return bool(_NUMBER.match(text) or _DATE.match(text))


@dataclass
class ChangeLog:
    """What each step changed, in the order it ran."""

    steps: List[str] = field(default_factory=list)

    def add(self, step: str, detail: str) -> None:
        self.steps.append(f"{step}: {detail}")

    def summary(self) -> str:
        return "\n".join(self.steps)


def _row_score(row: Sequence[str], next_row: Optional[Sequence[str]]) -> float:
    cells = [clean_text(cell) for cell in row]
    filled = [cell for cell in cells if cell]
    if len(filled) < 2:
        return -1.0
    fill = len(filled) / len(cells)
    textish = sum(0 if looks_numeric(cell) else 1 for cell in filled) / len(filled)
    unique = len(set(filled)) / len(filled)
    score = fill * 2 + textish * 2 + unique
    if next_row is not None and any(looks_numeric(cell) for cell in next_row):
        score += 1  # a row whose neighbour holds data is more likely the header
    return score


def detect_header_row(rows: Sequence[Sequence[str]], scan: int = 10) -> int:
    """Return the index of the row that looks most like a header.

    A Korean export often starts with ``2026년 1월 매출현황``, a blank row, and
    only then the column names. The winner is the best-scoring of the first
    ``scan`` rows that carry at least two filled cells; ties go to the earliest
    row, because the header comes before the data, never after it.
    """
    best_index, best_score = 0, float("-inf")
    for index, row in enumerate(rows[:scan]):
        if not row:
            continue
        next_row = rows[index + 1] if index + 1 < len(rows) else None
        score = _row_score(row, next_row)
        if score > best_score + 1e-9:
            best_index, best_score = index, score
    return best_index


def _strip_trailing_blanks(row: Sequence[str]) -> List[str]:
    cells = list(row)
    while cells and is_blank(cells[-1]):
        cells.pop()
    return cells


def _unique_header(cells: Sequence[str]) -> List[str]:
    """Duplicate column names get ``_2``, ``_3`` so ``row[col]`` never collides."""
    seen: dict = {}
    out: List[str] = []
    for index, cell in enumerate(cells, start=1):
        name = cell or f"col_{index}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        out.append(name)
    return out


def clean_rows(
    rows: Sequence[Sequence[str]],
    header_row: Optional[int] = None,
    dedupe: bool = False,
    nfkc: bool = True,
    log: Optional[ChangeLog] = None,
) -> Tuple[List[str], List[List[str]]]:
    """Return ``(header, body)`` with the steps recorded in ``log``.

    The order is deliberate: blanks out first (so an empty row cannot win the
    header vote), then the header, then per-cell text, then duplicates.
    """
    log = log if log is not None else ChangeLog()

    positions = [i for i, row in enumerate(rows) if any(not is_blank(cell) for cell in row)]
    kept = [list(rows[i]) for i in positions]
    if len(kept) != len(rows):
        log.add("drop_blank_rows", f"{len(rows) - len(kept)} removed")

    if not kept:
        return [], []

    width = max((len(_strip_trailing_blanks(row)) for row in kept), default=0)
    trimmed = sum(1 for row in kept if len(row) > len(_strip_trailing_blanks(row)))
    if trimmed:
        log.add("drop_empty_columns", f"{trimmed} rows padded")

    index = detect_header_row(kept) if header_row is None else header_row
    index = max(0, min(index, len(kept) - 1))
    if index:
        dropped = [clean_text(kept[i][0]) if kept[i] else "" for i in range(index)]
        original_row = positions[index] + 1
        log.add(
            "promote_header",
            f"used row {original_row} as header "
            f"(dropped: {', '.join(filter(None, dropped)) or 'blank rows'})",
        )

    header_cells = [clean_text(cell, nfkc) for cell in _strip_trailing_blanks(kept[index])]
    header = _unique_header(header_cells)
    body_raw = kept[index + 1:]

    body: List[List[str]] = []
    for row in body_raw:
        cells = [clean_text(cell, nfkc) for cell in _strip_trailing_blanks(row)]
        cells = (cells + [""] * len(header))[: len(header)]
        body.append(cells)

    changed = 0
    for row in body_raw:
        for cell in row:
            if str(cell) != clean_text(cell, nfkc) and not is_blank(cell):
                changed += 1
    if changed:
        log.add("clean_text", f"{changed} cells (invisible chars, full-width, spacing)")

    if dedupe:
        seen = set()
        unique: List[List[str]] = []
        for row in body:
            key = tuple(row)
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        if len(unique) != len(body):
            log.add("dedupe", f"{len(body) - len(unique)} duplicates removed, {len(body)}->{len(unique)} rows")
        body = unique

    return header, body


def preview(rows: Iterable[Sequence[str]], limit: int = 3) -> List[str]:
    """First few rows as ``a | b | c`` lines, for the CLI's inspect output."""
    return [" | ".join(cell for cell in row) for row in list(rows)[:limit]]
