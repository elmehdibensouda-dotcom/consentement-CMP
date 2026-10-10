"""Spreadsheet formula neutralization for audit and consent CSV exports."""
from __future__ import annotations

import csv
import io
import unittest

from backend.aman_api import main as api


def round_trip(values: list) -> list[str]:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\r\n").writerow([api.audit_csv_cell(value) for value in values])
    return next(csv.reader(io.StringIO(buffer.getvalue(), newline="")))


class CsvFormulaCellTests(unittest.TestCase):
    def test_formula_triggers_are_neutralized_after_csv_parsing(self) -> None:
        dangerous = [
            "=HYPERLINK(\"https://attacker.example\")", "+1+1", "-2+3", "@SUM(A1)",
            "\t=1+1", "\r=1+1", "\n=1+1", "   =1+1", "\tplain", "\rplain",
            "＝1+1", "＋1", "－1", "＠1",
        ]
        for original, parsed in zip(dangerous, round_trip(dangerous)):
            with self.subTest(value=repr(original)):
                self.assertTrue(parsed.startswith("'"), parsed)
                self.assertEqual(parsed[1:], original)

    def test_harmless_values_are_unchanged(self) -> None:
        harmless = ["abc", "1791628611", "", None, '{"role":"viewer"}', "a=b", "user@example.com",
                    "member.joined", "texte avec espace", "e-mail"]
        expected = ["" if value is None else value for value in harmless]
        self.assertEqual(round_trip(harmless), expected)


if __name__ == "__main__":
    unittest.main()
