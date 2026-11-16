"""The command line, run the way a user runs it."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from kcsvlite.cli import main

KOREAN_CSV = "고객명,금액\n김민수,1200\n"


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.source = os.path.join(self.dir, "report.csv")
        with open(self.source, "wb") as fh:
            fh.write(KOREAN_CSV.encode("cp949"))

    def run_cli(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_inspect_reports_the_encoding(self):
        code, output = self.run_cli(["inspect", self.source])
        self.assertEqual(code, 0)
        self.assertIn("encoding  : cp949", output)
        self.assertIn("고객명", output)

    def test_clean_writes_a_utf8_file(self):
        target = os.path.join(self.dir, "clean.csv")
        code, output = self.run_cli(["clean", self.source, "-o", target])
        self.assertEqual(code, 0)
        self.assertIn("written", output)
        with open(target, "rb") as fh:
            self.assertTrue(fh.read().startswith(b"\xef\xbb\xbf"))

    def test_clean_names_the_output_when_none_is_given(self):
        code, output = self.run_cli(["clean", self.source])
        self.assertEqual(code, 0)
        self.assertIn("report_clean.csv", output)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "report_clean.csv")))

    def test_clean_on_an_empty_file_fails_cleanly(self):
        empty = os.path.join(self.dir, "empty.csv")
        open(empty, "w").close()
        code, _ = self.run_cli(["clean", empty])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
