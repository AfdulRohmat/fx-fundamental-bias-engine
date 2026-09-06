from __future__ import annotations

import unittest

from fx_fundamental_bias.phase04_fx import _average_ranks, _correlation, _slope


class Phase04FxTests(unittest.TestCase):
    def test_average_rank_handles_ties(self) -> None:
        self.assertEqual(
            _average_ranks({"A": 1.0, "B": 1.0, "C": 3.0}),
            {"A": 1.5, "B": 1.5, "C": 3.0},
        )

    def test_positive_pressure_return_relation_has_positive_slope(self) -> None:
        rows = [
            {"pair_pressure_bp": value, "pair_return_log": 2.0 * value}
            for value in (-2.0, -1.0, 1.0, 2.0)
        ]
        self.assertAlmostEqual(_slope(rows), 2.0)

    def test_rank_correlation_orientation(self) -> None:
        self.assertAlmostEqual(_correlation([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(_correlation([1, 2, 3], [3, 2, 1]), -1.0)


if __name__ == "__main__":
    unittest.main()
