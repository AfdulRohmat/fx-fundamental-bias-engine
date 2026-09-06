from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fx_fundamental_bias.eiopa_rfr import G10_CURRENCIES
from fx_fundamental_bias.qualification import (
    FIELDS,
    REQUIRED_FEATURES,
    QualificationError,
    load_catalog,
    summarize,
)


def _rows() -> list[dict[str, object]]:
    return [
        {
            "currency": currency,
            "feature": feature,
            "provider": "test",
            "series_id": "test",
            "frequency": "monthly",
            "coverage_start": "2015-01-01",
            "coverage_end": "open",
            "publication_time_status": "verified",
            "vintage_status": "not_applicable",
            "expectation_kind": "not_applicable",
            "license_status": "reviewed",
            "missing_rate": "not_measured",
            "decision": "PASS",
            "limitation": "none",
        }
        for currency in sorted(G10_CURRENCIES)
        for feature in sorted(REQUIRED_FEATURES)
    ]


class QualificationTests(unittest.TestCase):
    def test_repository_catalog_expands_to_complete_g10_matrix(self) -> None:
        path = Path(__file__).parents[1] / "config" / "phase01_sources.json"
        rows = load_catalog(path)
        result = summarize(rows)

        self.assertEqual(result["row_count"], 70)
        self.assertEqual(
            result["decision_counts"],
            {"FAIL": 10, "PASS": 10, "REVIEW_REQUIRED": 50},
        )
        self.assertEqual(result["phase_decision"], "REVIEW_REQUIRED")
        self.assertFalse(
            any("{" in str(row["series_id"]) for row in rows),
            "Every generated source row must have a concrete series identifier",
        )

    def test_complete_matrix_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps({"rows": _rows()}), encoding="utf-8")
            rows = load_catalog(path)
            result = summarize(rows)

        self.assertEqual(len(FIELDS), 14)
        self.assertEqual(result["row_count"], 70)
        self.assertTrue(result["all_required_rows_pass"])

    def test_missing_currency_feature_fails_closed(self) -> None:
        rows = _rows()
        rows.pop()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
            with self.assertRaisesRegex(QualificationError, "key mismatch"):
                load_catalog(path)


if __name__ == "__main__":
    unittest.main()
