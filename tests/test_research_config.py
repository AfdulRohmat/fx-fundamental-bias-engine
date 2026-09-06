from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fx_fundamental_bias.research_config import (
    ResearchConfigError,
    load_research_config,
)


class ResearchConfigTests(unittest.TestCase):
    def test_registered_proxy_config_is_valid(self) -> None:
        path = Path(__file__).parents[1] / "config" / "research_proxy_v0_2.json"
        config = load_research_config(path)

        self.assertEqual(len(config.currencies), 10)
        self.assertEqual(config.expectation_kind, "EIOPA_RFR_1Y_PROXY")
        self.assertLess(config.label_support_end, config.sealed_start)
        self.assertEqual(config.bootstrap.resamples, 10000)

    def test_rejects_config_that_reaches_sealed_period(self) -> None:
        source = Path(__file__).parents[1] / "config" / "research_proxy_v0_2.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        document["label_support_end"] = "2025-01-31"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ResearchConfigError, "date boundaries"):
                load_research_config(path)


if __name__ == "__main__":
    unittest.main()
