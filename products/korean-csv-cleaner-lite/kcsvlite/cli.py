"""Command line: ``python -m kcsvlite inspect|clean FILE``."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .clean import ChangeLog, clean_rows, detect_header_row
from .encoding import read_rows, write_rows


def _inspect(path: str, delimiter: Optional[str]) -> int:
    rows, encoding, sep = read_rows(path, delimiter)
    width = max((len(row) for row in rows), default=0)
    print(f"file      : {path}")
    print(f"encoding  : {encoding}")
    print(f"delimiter : {sep!r}")
    print(f"rows      : {len(rows)} x {width}")
    if not rows:
        print("header    : (empty file)")
        return 0
    index = detect_header_row(rows)
    header = " | ".join(cell for cell in rows[index])
    print(f"header    : row {index + 1} -> {header}")
    print("first rows:")
    for number, row in enumerate(rows[:3], start=1):
        print(f"  {number}: {' | '.join(row)}")
    return 0


def _clean(args: argparse.Namespace) -> int:
    rows, encoding, sep = read_rows(args.source, args.delimiter)
    log = ChangeLog()
    header, body = clean_rows(
        rows,
        header_row=args.header_row,
        dedupe=args.dedupe,
        nfkc=not args.no_nfkc,
        log=log,
    )
    if not header:
        print(f"{args.source}: nothing to clean (empty file)", file=sys.stderr)
        return 1
    out = args.output or (args.source.rsplit(".", 1)[0] + "_clean.csv")
    write_rows([header] + body, out, encoding="utf-8-sig", delimiter=sep)
    print(f"{args.source}: read {len(rows)} rows as {encoding}")
    print(log.summary() or "no changes needed")
    print(f"written   : {out}  ({len(body)} rows x {len(header)} columns, utf-8-sig)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kcsvlite",
        description="Open and clean Korean CSV exports (CP949/EUC-KR/UTF-8) offline.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="encoding, delimiter, shape, header")
    inspect.add_argument("source")
    inspect.add_argument("--delimiter", default=None)

    clean = sub.add_parser("clean", help="write a normalised UTF-8 CSV + change log")
    clean.add_argument("source")
    clean.add_argument("-o", "--output", default=None)
    clean.add_argument("--delimiter", default=None)
    clean.add_argument("--header-row", type=int, default=None,
                       help="0-based index of the header row (default: detect)")
    clean.add_argument("--dedupe", action="store_true", help="drop exact duplicate rows")
    clean.add_argument("--no-nfkc", action="store_true",
                       help="keep full-width characters as they are")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect":
        return _inspect(args.source, args.delimiter)
    return _clean(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
