#!/usr/bin/env python3
"""Run the cleaner on the bundled samples and print what it changed."""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kcsvlite import ChangeLog, clean_rows, read_rows, write_rows  # noqa: E402

OUT = os.path.join(HERE, "out")


def run(name: str, dedupe: bool = False) -> None:
    source = os.path.join(HERE, "examples", name)
    rows, encoding, sep = read_rows(source)
    log = ChangeLog()
    header, body = clean_rows(rows, dedupe=dedupe, log=log)
    target = os.path.join(OUT, name.rsplit(".", 1)[0] + "_clean.csv")
    write_rows([header] + body, target)
    print(f"{name}: {len(rows)} rows read as {encoding}, {len(header)} columns")
    print(log.summary() or "  no changes needed")
    print(f"  -> {os.path.relpath(target, HERE)}\n")


if __name__ == "__main__":
    run("report_cp949.csv", dedupe=True)
    run("vendors_utf8_bom.csv")
