"""Build the sample files in ``examples/`` (kept 1-2 KB each on purpose)."""
from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "examples")

# A report as it really arrives from a Korean ERP: a title row, a blank line,
# then the header. CP949 on disk, an ideographic space inside one name,
# full-width digits in one amount, and one customer listed twice.
REPORT = [
    ["2026년 1월 고객 명세"],
    [],
    ["고객명", "휴대폰_번호", "가입일", "누적구매액", "수신동의"],
    ["(주)대한물산", "010-1234-5678", "2024.01.05", "1,200,000원", "Y"],
    ["\u3000김민수", "010 5555 1234", "24-1-7", "\uff11\uff12\uff13\uff10\uff10\uff10", "N"],
    ["이서연", "+82 10-2222-3333", "2024년 1월 9일", "540,000", "Y"],
    ["박지훈", "010 7777 8888", "20240112", "0", "N"],
    [],
    ["최유진", "010-9999-0000", "2024.02.01", "3,300,000", "Y"],
    ["최유진", "010-9999-0000", "2024.02.01", "3,300,000", "Y"],
]

# A vendor list from a procurement system: semicolon separated, UTF-8 with a
# BOM, a non-breaking space inside one phone number, and a soft hyphen that
# makes a search for "서연상회" fail even though it looks right on screen.
VENDORS = [
    ["사업자번호", "회사명", "담당자", "연락처"],
    ["123-45-67890", "대한물산", "김민수", "02-555-0100"],
    ["234-56-78901", "서\u00ad연상회", "이서연", "02\u00a0555\u00a00200"],
    ["345-67-89012", "동백통", "박지훈", "051-555-0300"],
]


def _write(path: str, rows, encoding: str, delimiter: str) -> None:
    with open(path, "w", encoding=encoding, newline="") as fh:
        writer = csv.writer(fh, delimiter=delimiter, lineterminator="\n")
        writer.writerows(rows)


def main() -> None:
    os.makedirs(EXAMPLES, exist_ok=True)

    cp949 = os.path.join(EXAMPLES, "report_cp949.csv")
    _write(cp949, REPORT, "cp949", ",")

    vendors = os.path.join(EXAMPLES, "vendors_utf8_bom.csv")
    _write(vendors, VENDORS, "utf-8-sig", ";")

    print(f"wrote {cp949}")
    print(f"wrote {vendors}")


if __name__ == "__main__":
    main()
