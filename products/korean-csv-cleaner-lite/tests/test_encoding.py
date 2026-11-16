"""Encoding detection, delimiter sniffing and the read/write round trip."""
from __future__ import annotations

import os
import tempfile
import unittest

from kcsvlite.encoding import (
    decode_bytes,
    detect_encoding,
    read_rows,
    sniff_delimiter,
    write_rows,
)

KOREAN = "고객명,휴대폰_번호\n김민수,010-1234-5678\n"


class DetectEncodingTest(unittest.TestCase):
    def test_utf8_with_bom(self):
        self.assertEqual(detect_encoding(b"\xef\xbb\xbf" + KOREAN.encode("utf-8")), "utf-8-sig")

    def test_utf8_without_bom(self):
        self.assertEqual(detect_encoding(KOREAN.encode("utf-8")), "utf-8")

    def test_cp949(self):
        self.assertEqual(detect_encoding(KOREAN.encode("cp949")), "cp949")

    def test_cp949_bytes_are_not_readable_as_utf8(self):
        raw = KOREAN.encode("cp949")
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")

    def test_unknown_bytes_fall_back_to_latin1(self):
        self.assertEqual(detect_encoding(b"\xff\xff\xff\xff"), "latin-1")

    def test_bom_is_removed_from_the_text(self):
        text, encoding = decode_bytes(b"\xef\xbb\xbfid,name\n1,a\n")
        self.assertEqual(encoding, "utf-8-sig")
        self.assertTrue(text.startswith("id,name"))
        self.assertNotIn("\ufeff", text)


class SniffDelimiterTest(unittest.TestCase):
    def test_comma(self):
        self.assertEqual(sniff_delimiter("a,b,c\n1,2,3\n"), ",")

    def test_semicolon(self):
        self.assertEqual(sniff_delimiter("a;b;c\n1;2;3\n"), ";")

    def test_tab(self):
        self.assertEqual(sniff_delimiter("a\tb\tc\n1\t2\t3\n"), "\t")

    def test_pipe(self):
        self.assertEqual(sniff_delimiter("a|b|c\n1|2|3\n"), "|")

    def test_single_column_defaults_to_comma(self):
        self.assertEqual(sniff_delimiter("one\ntwo\n"), ",")


class ReadWriteTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def _path(self, name: str) -> str:
        return os.path.join(self.dir, name)

    def test_reads_cp949_into_a_raw_grid(self):
        path = self._path("report.csv")
        with open(path, "wb") as fh:
            fh.write(KOREAN.encode("cp949"))
        rows, encoding, delimiter = read_rows(path)
        self.assertEqual(encoding, "cp949")
        self.assertEqual(delimiter, ",")
        self.assertEqual(rows[0], ["고객명", "휴대폰_번호"])
        self.assertEqual(rows[1], ["김민수", "010-1234-5678"])

    def test_no_header_is_assumed(self):
        path = self._path("plain.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("id,name\n1,a\n")
        rows, _, _ = read_rows(path)
        self.assertEqual(rows[0], ["id", "name"])
        self.assertEqual(len(rows), 2)

    def test_written_file_starts_with_a_bom(self):
        path = self._path("out.csv")
        write_rows([["a", "b"], ["1", "2"]], path)
        with open(path, "rb") as fh:
            self.assertTrue(fh.read().startswith(b"\xef\xbb\xbf"))

    def test_round_trip_keeps_korean(self):
        path = self._path("round.csv")
        write_rows([["고객명"], ["김민수"]], path)
        rows, encoding, _ = read_rows(path)
        self.assertEqual(encoding, "utf-8-sig")
        self.assertEqual(rows, [["고객명"], ["김민수"]])

    def test_semicolon_is_kept_on_write(self):
        path = self._path("semi.csv")
        write_rows([["a", "b"], ["1", "2"]], path, delimiter=";")
        with open(path, encoding="utf-8-sig") as fh:
            self.assertIn(";", fh.read())


if __name__ == "__main__":
    unittest.main()
