"""Text cleanup, header detection and the cleaning pipeline."""
from __future__ import annotations

import unittest

from kcsvlite.clean import (
    ChangeLog,
    clean_rows,
    clean_text,
    detect_header_row,
    is_blank,
    looks_numeric,
)


class IsBlankTest(unittest.TestCase):
    def test_none(self):
        self.assertTrue(is_blank(None))

    def test_empty(self):
        self.assertTrue(is_blank(""))

    def test_spaces(self):
        self.assertTrue(is_blank("   "))

    def test_non_breaking_space(self):
        self.assertTrue(is_blank("\u00a0"))

    def test_value(self):
        self.assertFalse(is_blank("0"))


class CleanTextTest(unittest.TestCase):
    def test_non_breaking_space_becomes_space(self):
        self.assertEqual(clean_text("02\u00a0555\u00a00100"), "02 555 0100")

    def test_ideographic_space_is_trimmed(self):
        self.assertEqual(clean_text("\u3000김민수"), "김민수")

    def test_zero_width_characters_are_removed(self):
        self.assertEqual(clean_text("서\u200b연"), "서연")

    def test_soft_hyphen_is_removed(self):
        self.assertEqual(clean_text("서\u00ad연상회"), "서연상회")

    def test_full_width_digits_become_plain(self):
        self.assertEqual(clean_text("１２３０００"), "123000")

    def test_whitespace_runs_collapse(self):
        self.assertEqual(clean_text("  a   b  "), "a b")

    def test_nfkc_can_be_switched_off(self):
        self.assertEqual(clean_text("１２３", nfkc=False), "１２３")

    def test_blank_stays_blank(self):
        self.assertEqual(clean_text(None), "")


class LooksNumericTest(unittest.TestCase):
    def test_plain_number(self):
        self.assertTrue(looks_numeric("1200"))

    def test_thousands_separator(self):
        self.assertTrue(looks_numeric("1,200,000"))

    def test_dotted_date(self):
        self.assertTrue(looks_numeric("2024.01.05"))

    def test_korean_date(self):
        self.assertTrue(looks_numeric("2024년 1월 5일"))

    def test_label(self):
        self.assertFalse(looks_numeric("고객명"))

    def test_empty(self):
        self.assertFalse(looks_numeric(""))


class HeaderDetectionTest(unittest.TestCase):
    def test_header_on_first_row(self):
        rows = [["이름", "나이"], ["김민수", "31"], ["이서연", "28"]]
        self.assertEqual(detect_header_row(rows), 0)

    def test_title_row_above_header(self):
        rows = [["2026년 1월 고객 명세"], [], ["고객명", "가입일", "금액"], ["김민수", "2024.01.05", "1200"]]
        self.assertEqual(detect_header_row(rows), 2)

    def test_single_row_file_is_the_header(self):
        self.assertEqual(detect_header_row([["a", "b"]]), 0)


class CleanRowsTest(unittest.TestCase):
    def test_promotes_the_header_and_drops_blanks(self):
        rows = [["2026년 1월 매출"], [], ["고객명", "금액"], ["김민수", "1200"]]
        log = ChangeLog()
        header, body = clean_rows(rows, log=log)
        self.assertEqual(header, ["고객명", "금액"])
        self.assertEqual(body, [["김민수", "1200"]])
        self.assertIn("promote_header", log.summary())
        self.assertIn("drop_blank_rows", log.summary())

    def test_rows_are_padded_to_the_header_width(self):
        rows = [["a", "b", "c"], ["1", "2"]]
        header, body = clean_rows(rows)
        self.assertEqual(header, ["a", "b", "c"])
        self.assertEqual(body, [["1", "2", ""]])

    def test_duplicate_header_names_get_a_suffix(self):
        header, _ = clean_rows([["금액", "금액", "비고"], ["1", "2", "3"]])
        self.assertEqual(header, ["금액", "금액_2", "비고"])

    def test_unnamed_column_gets_a_placeholder(self):
        header, _ = clean_rows([["a", "", "c"], ["1", "2", "3"]])
        self.assertEqual(header, ["a", "col_2", "c"])

    def test_trailing_empty_columns_are_dropped(self):
        header, body = clean_rows([["a", "b", ""], ["1", "2", ""]])
        self.assertEqual(header, ["a", "b"])
        self.assertEqual(body, [["1", "2"]])

    def test_dedupe_removes_exact_duplicate_rows(self):
        rows = [["a", "b"], ["1", "2"], ["1", "2"], ["3", "4"]]
        log = ChangeLog()
        _, body = clean_rows(rows, dedupe=True, log=log)
        self.assertEqual(body, [["1", "2"], ["3", "4"]])
        self.assertIn("duplicate", log.summary())

    def test_without_dedupe_nothing_is_merged(self):
        rows = [["a", "b"], ["1", "2"], ["1", "2"]]
        _, body = clean_rows(rows)
        self.assertEqual(len(body), 2)

    def test_cells_are_cleaned(self):
        rows = [["고객명", "금액"], ["\u3000김민수", "１２３"]]
        _, body = clean_rows(rows)
        self.assertEqual(body, [["김민수", "123"]])

    def test_empty_file_returns_nothing(self):
        header, body = clean_rows([[], ["   "]])
        self.assertEqual(header, [])
        self.assertEqual(body, [])

    def test_explicit_header_row_wins(self):
        rows = [["제목"], ["a", "b"], ["1", "2"]]
        header, body = clean_rows(rows, header_row=1)
        self.assertEqual(header, ["a", "b"])
        self.assertEqual(body, [["1", "2"]])


class ChangeLogTest(unittest.TestCase):
    def test_empty_summary_is_empty_string(self):
        self.assertEqual(ChangeLog().summary(), "")

    def test_steps_keep_their_order(self):
        log = ChangeLog()
        log.add("first", "1")
        log.add("second", "2")
        self.assertEqual(log.summary(), "first: 1\nsecond: 2")


if __name__ == "__main__":
    unittest.main()
