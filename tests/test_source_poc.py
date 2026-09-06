from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from fx_fundamental_bias.source_poc import (
    audit_alfred_vintages,
    audit_bis_policy_rates,
    audit_ecb_fx,
)


class SourcePocTests(unittest.TestCase):
    def test_alfred_detects_revision_between_vintages(self) -> None:
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "vintages.csv",
                "observation_date,CPI_20181231,CPI_20241231\n"
                "2018-01-01,2.0,2.1\n2018-02-01,2.2,2.2\n",
            )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "alfred.zip"
            path.write_bytes(payload.getvalue())
            result = audit_alfred_vintages(path)

        self.assertEqual(result.series_id, "CPI")
        self.assertEqual(result.changed_cell_count, 1)
        self.assertEqual(result.comparable_cell_count, 2)

    def test_ecb_derives_usdjpy_from_eur_legs(self) -> None:
        header = "CURRENCY,CURRENCY_DENOM,TIME_PERIOD,OBS_VALUE\n"
        rows = "".join(
            f"{currency},EUR,2024-12-31,{value}\n"
            for currency, value in {
                "AUD": 1.6,
                "CAD": 1.5,
                "CHF": 0.94,
                "GBP": 0.83,
                "JPY": 162.0,
                "NOK": 11.8,
                "NZD": 1.8,
                "SEK": 11.5,
                "USD": 1.08,
            }.items()
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ecb.csv"
            path.write_text(header + rows, encoding="utf-8")
            result = audit_ecb_fx(path)

        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["cross_example"]["rate"], 150.0)

    def test_bis_requires_all_g10_policy_rates(self) -> None:
        header = "FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE,COMPILATION\n"
        areas = ("AU", "CA", "CH", "XM", "GB", "JP", "NO", "NZ", "SE", "US")
        rows = "".join(f"D,{area},2024-12-31,1.25,test definition\n" for area in areas)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bis.csv"
            path.write_text(header + rows, encoding="utf-8")
            result = audit_bis_policy_rates(path)

        self.assertEqual(result["status"], "PASS_FOR_SCALAR_HISTORY")
        self.assertEqual(len(result["currencies"]), 10)


if __name__ == "__main__":
    unittest.main()
