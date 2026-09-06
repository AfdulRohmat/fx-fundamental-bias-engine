from __future__ import annotations

import unittest

from fx_fundamental_bias.phase02_fetch import parse_eiopa_links


class Phase02FetchTests(unittest.TestCase):
    def test_extracts_monthly_zip_and_ignores_non_monthly_file(self) -> None:
        html = b"""
        <div class="ecl-file"><div class="ecl-file__title">December 2022</div>
        <a href="/document/download/id?filename=December%202022.zip"
        class="ecl-link ecl-file__download">Download</a></div>
        <div class="ecl-file"><div class="ecl-file__title">Technical docs</div>
        <a href="/document/docs.pdf" class="ecl-file__download">Download</a></div>
        """
        result = parse_eiopa_links((html,))

        self.assertEqual(set(result), {"2022-12"})
        self.assertTrue(result["2022-12"].startswith("https://www.eiopa.europa.eu/"))


if __name__ == "__main__":
    unittest.main()
