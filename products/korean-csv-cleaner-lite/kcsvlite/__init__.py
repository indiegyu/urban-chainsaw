"""A small, dependency-free cleaner for Korean CSV exports.

Two jobs, one command each: **open the file you were sent** and **make it
consistent enough to merge, upload or hand over**. Everything runs locally.
"""
from .clean import (
    ChangeLog,
    clean_rows,
    clean_text,
    detect_header_row,
    is_blank,
    looks_numeric,
)
from .encoding import (
    CANDIDATE_ENCODINGS,
    decode_bytes,
    detect_encoding,
    read_rows,
    sniff_delimiter,
    write_rows,
)

__version__ = "1.0.0"

__all__ = [
    "CANDIDATE_ENCODINGS",
    "ChangeLog",
    "clean_rows",
    "clean_text",
    "decode_bytes",
    "detect_encoding",
    "detect_header_row",
    "is_blank",
    "looks_numeric",
    "read_rows",
    "sniff_delimiter",
    "write_rows",
    "__version__",
]
