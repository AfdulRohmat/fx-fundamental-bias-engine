from __future__ import annotations

import unittest
from datetime import date

from fx_fundamental_bias.phase02_panel import _latest_feature, _zscore


class Phase02PanelTests(unittest.TestCase):
    def test_zscore_uses_only_values_before_current_observation(self) -> None:
        items = [(date(2000 + index, 1, 1), float(index)) for index in range(5)]
        before = _zscore(items, 4, 3)
        mutated = [*items, (date(2030, 1, 1), 1_000_000.0)]
        self.assertEqual(before, _zscore(mutated, 4, 3))

    def test_stale_feature_fails_closed(self) -> None:
        result = _latest_feature(
            [(date(2021, 1, 31), 1.0), (date(2021, 2, 28), 2.0)],
            snapshot=date(2021, 12, 31),
            frequency="monthly",
            minimum=1,
        )
        self.assertIsNone(result.raw)
        self.assertIsNone(result.z)
        self.assertEqual(result.reference_period, date(2021, 2, 28))


if __name__ == "__main__":
    unittest.main()
