from __future__ import annotations

import unittest

from fx_fundamental_bias.ridge import predict, ridge_fit


class RidgeTests(unittest.TestCase):
    def test_fits_a_small_linear_relation(self) -> None:
        design = [[1.0, value] for value in (0.0, 1.0, 2.0, 3.0)]
        target = [1.0, 3.0, 5.0, 7.0]
        coefficients = ridge_fit(
            design,
            target,
            penalty=0.0,
            unpenalized=frozenset({0}),
        )
        self.assertAlmostEqual(predict([1.0, 4.0], coefficients), 9.0, places=6)

    def test_nonnegative_constraint_removes_negative_slope(self) -> None:
        design = [[1.0, value] for value in (0.0, 1.0, 2.0, 3.0)]
        target = [3.0, 2.0, 1.0, 0.0]
        coefficients = ridge_fit(
            design,
            target,
            penalty=0.0,
            unpenalized=frozenset({0}),
            nonnegative=frozenset({1}),
        )
        self.assertEqual(coefficients[1], 0.0)


if __name__ == "__main__":
    unittest.main()
