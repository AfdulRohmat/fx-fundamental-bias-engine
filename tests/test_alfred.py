from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from fx_fundamental_bias.alfred import (
    build_request,
    chunk_vintage_dates,
    merge_tables,
    parse_package,
)


def _package(header: str, row: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("vintages.csv", f"observation_date,{header}\n{row}\n")
    return buffer.getvalue()


class AlfredTests(unittest.TestCase):
    def test_chunks_requests_below_form_limit(self) -> None:
        dates = tuple(
            date(year, month, 1) for year in range(2015, 2020) for month in range(1, 13)
        )
        chunks = chunk_vintage_dates(dates, maximum_per_request=20)

        self.assertEqual([len(chunk) for chunk in chunks], [20, 20, 20])
        for chunk in chunks:
            payload = build_request(
                observation_start=date(2000, 1, 1),
                observation_end=date(2020, 1, 1),
                vintages=chunk,
            )
            self.assertLessEqual(len(" ".join(str(value) for value in chunk)), 500)
            self.assertIn(b"form%5Bfile_type%5D=2", payload)

    def test_parses_and_merges_non_overlapping_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.zip"
            second = Path(temporary) / "second.zip"
            first.write_bytes(_package("CPI_20200131", "2019-12-01,100"))
            second.write_bytes(_package("CPI_20200229", "2019-12-01,101"))
            table = merge_tables((parse_package(first), parse_package(second)))

        self.assertEqual(table.series_id, "CPI")
        self.assertEqual(table.value(date(2019, 12, 1), date(2020, 1, 31)), 100)
        self.assertEqual(table.value(date(2019, 12, 1), date(2020, 2, 29)), 101)


if __name__ == "__main__":
    unittest.main()
