"""Regression tests for the fictional insurer and bank seed policies."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed_demo import demo_policy


class DemoSeedTests(unittest.TestCase):
    def test_insurance_policy_uses_insurance_controller_label_in_arabic_notice(self) -> None:
        policy = demo_policy(
            "insurance-property",
            "web",
            180,
            "Entité d’assurance fictive de démonstration",
            "كيان تأمين افتراضي لأغراض العرض التوضيحي",
        )

        self.assertEqual(
            policy["noticeTranslations"]["ar"]["controllerName"],
            "كيان تأمين افتراضي لأغراض العرض التوضيحي",
        )
        self.assertEqual(policy["notice"]["controllerName"], "Entité d’assurance fictive de démonstration")

    def test_bank_policy_keeps_bank_controller_label_in_arabic_notice(self) -> None:
        policy = demo_policy(
            "bank-property",
            "web",
            180,
            "Entité bancaire fictive de démonstration",
            "كيان مصرفي افتراضي لأغراض العرض التوضيحي",
        )

        self.assertEqual(
            policy["noticeTranslations"]["ar"]["controllerName"],
            "كيان مصرفي افتراضي لأغراض العرض التوضيحي",
        )


if __name__ == "__main__":
    unittest.main()
