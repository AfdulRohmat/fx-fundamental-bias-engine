from __future__ import annotations

import unittest
from datetime import date

from fx_fundamental_bias.phase03_models import block_bootstrap_ci


class Phase03ModelTests(unittest.TestCase):
    def test_bootstrap_is_deterministic_and_date_clustered(self) -> None:
        values = {
            date(2021, month, 28): [float(month), float(month + 1)]
            for month in range(1, 7)
        }
        first = block_bootstrap_ci(
            values, block_length=3, resamples=100, seed=42
        )
        second = block_bootstrap_ci(
            values, block_length=3, resamples=100, seed=42
        )
        self.assertEqual(first, second)
        self.assertLess(first[0], first[1])


if __name__ == "__main__":
    unittest.main()
