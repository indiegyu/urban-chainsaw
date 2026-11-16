"""Reading CSV files that came from somewhere else.

A Korean office export is usually **CP949** — the encoding Excel on a Korean
Windows machine writes when you pick "CSV (쉼표로 분리)". Opening it as UTF-8
raises ``UnicodeDecodeError``; opening a UTF-8 file as CP949 gives mojibake that
saves fine and is wrong forever. So try the encodings in the order they fail,
and never guess silently.
"""
from __future__ import annotations

import csv
import io
import os
from typing import Iterable, List, Sequence, Tuple

# Order matters. utf-8-sig first (a BOM is legal UTF-8 and stripping it here
# saves the "ï»¿id" first column), then plain utf-8, then the Korean pair,
# then latin-1 which decodes anything — so it can only ever be the last resort.
CANDIDATE_ENCODINGS: Tuple[str, ...] = ("utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1")

BOM = b"\xef\xbb\xbf"
_BOMS = {b"\xef\xbb\xbf": "utf-8-sig", b"\xff\xfe\x00\x00": "utf-32", b"\xff\xfe": "utf-16", b"\xfe\xff": "utf-16"}


def detect_encoding(raw: bytes, candidates: Iterable[str] = CANDIDATE_ENCODINGS) -> str:
    """Return the first candidate that decodes ``raw`` strictly.

    A byte-order mark is trusted first: it is an explicit declaration, not a
    heuristic. After that the candidates are tried in order and the first one
    that does not raise wins.
    """
    for bom, name in _BOMS.items():
        if raw.startswith(bom):
            return name
    for enc in candidates:
        if enc == "utf-8-sig":
            continue  # only meaningful when the file actually carries a BOM
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "latin-1"


def decode_bytes(raw: bytes) -> Tuple[str, str]:
    """``(text, encoding)`` with the BOM removed from ``text``."""
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    return text, encoding


def sniff_delimiter(sample: str) -> str:
    """Guess ``,`` ``;`` ``\\t`` ``|`` from the first lines of the file."""
    head = "\n".join(sample.splitlines()[:10])
    try:
        return csv.Sniffer().sniff(head, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {d: head.count(d) for d in (",", ";", "\t", "|")}
        best = max(counts, key=counts.get)
        return best if counts[best] else ","


def read_rows(path: str, delimiter: str | None = None) -> Tuple[List[List[str]], str, str]:
    """Read any CSV into a raw grid. Returns ``(rows, encoding, delimiter)``.

    The file is read as a **grid with no header assumption** — a cleaner's job
    is to see what is actually in the file, including the title row a Korean
    Excel export puts above the real header, and then decide which row is the
    header. ``clean.clean_rows`` makes that decision.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    text, encoding = decode_bytes(raw)
    sep = delimiter or sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=sep)
    rows = [list(row) for row in reader]
    return rows, encoding, sep


def write_rows(
    rows: Sequence[Sequence[str]],
    path: str,
    encoding: str = "utf-8-sig",
    delimiter: str = ",",
) -> str:
    """Write a CSV that Excel opens without mojibake on both platforms.

    ``utf-8-sig`` is the default because Korean Excel reads a BOM-less file as
    CP949 and shows ``Ã«Â³Â´êÂ³`` — the same problem this module starts with.
    """
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding=encoding, newline="") as fh:
        writer = csv.writer(fh, delimiter=delimiter, lineterminator="\n")
        writer.writerows(rows)
    return path
