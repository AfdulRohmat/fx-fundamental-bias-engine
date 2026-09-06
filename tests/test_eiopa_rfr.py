from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from fx_fundamental_bias.eiopa_rfr import (
    G10_COUNTRY_TO_CURRENCY,
    EiopaRfrError,
    parse_term_structures,
)


def _workbook(*, omit_country: str | None = None) -> bytes:
    countries = [
        country for country in G10_COUNTRY_TO_CURRENCY if country != omit_country
    ]
    strings: list[str] = []
    cells_2: list[str] = []
    cells_3: list[str] = []
    cells_11 = ['<c r="B11"><v>1</v></c>']
    for index, country in enumerate(countries, start=3):
        column = chr(64 + index)
        area = "EU" if country == "Euro" else country[:2].upper()
        country_index = len(strings)
        strings.append(country)
        curve_index = len(strings)
        strings.append(f"{area}_31_12_2024_SWP_TEST")
        cells_2.append(f'<c r="{column}2" t="s"><v>{country_index}</v></c>')
        cells_3.append(f'<c r="{column}3" t="s"><v>{curve_index}</v></c>')
        cells_11.append(f'<c r="{column}11"><v>{index / 1000}</v></c>')
    shared = (
        '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main">'
        + "".join(f"<si><t>{value}</t></si>" for value in strings)
        + "</sst>"
    )
    workbook = (
        '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships"><sheets><sheet '
        'name="RFR_spot_no_VA" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.'
        'org/package/2006/relationships"><Relationship Id="rId1" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    sheet = (
        '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData><row r="2">'
        + "".join(cells_2)
        + '</row><row r="3">'
        + "".join(cells_3)
        + '</row><row r="11">'
        + "".join(cells_11)
        + "</row></sheetData></worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


class EiopaRfrTests(unittest.TestCase):
    def test_reads_all_g10_one_year_curves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "term_structures.xlsx"
            path.write_bytes(_workbook())
            points = parse_term_structures(path)

        self.assertEqual(len(points), 10)
        self.assertEqual(
            {point.currency for point in points},
            set(G10_COUNTRY_TO_CURRENCY.values()),
        )
        self.assertEqual({point.source_instrument for point in points}, {"SWP"})
        self.assertEqual(
            {point.reference_date.isoformat() for point in points},
            {"2024-12-31"},
        )

    def test_fails_closed_when_one_g10_curve_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "term_structures.xlsx"
            path.write_bytes(_workbook(omit_country="Japan"))
            with self.assertRaisesRegex(EiopaRfrError, "JPY"):
                parse_term_structures(path)

    def test_rejects_six_month_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "term_structures.xlsx"
            path.write_bytes(_workbook())
            with self.assertRaisesRegex(ValueError, "below one year"):
                parse_term_structures(path, maturity_years=0)


if __name__ == "__main__":
    unittest.main()
