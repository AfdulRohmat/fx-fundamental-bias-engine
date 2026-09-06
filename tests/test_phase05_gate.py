from __future__ import annotations

import unittest

from fx_fundamental_bias.phase05_gate import PROCEED, STOP, evaluate_gate


def _phase_summaries() -> tuple[dict[str, object], ...]:
    phase02 = {
        "status": "PASS",
        "evaluation_complete_row_count": 240,
        "evaluation_row_count": 240,
        "sealed_data_accessed": False,
    }
    phase03 = {
        "FB_H1_POLICY_SKILL_P1Y": "SUPPORTED",
        "FB_H2_PROXY_REPRICING_SKILL_P1Y": "SUPPORTED",
        "sealed_data_accessed": False,
    }
    phase04 = {
        "FB_H3_PAIR_DIRECTION_P1Y": "SUPPORTED",
        "FB_H4_RANK_IC_P1Y": "SUPPORTED",
        "FB_H5_EXTREME_SPREAD_P1Y": "NOT_SUPPORTED",
        "FB_H6_STABILITY_P1Y": "SUPPORTED",
        "fx_marks_non_executable": True,
        "profitability_claim": False,
        "sealed_data_accessed": False,
    }
    return phase02, phase03, phase04


class Phase05GateTests(unittest.TestCase):
    def test_proceeds_only_when_every_mandatory_gate_passes(self) -> None:
        result = evaluate_gate(*_phase_summaries())
        self.assertEqual(result["decision"], PROCEED)

    def test_not_tested_hypothesis_fails_closed(self) -> None:
        phase02, phase03, phase04 = _phase_summaries()
        phase03["FB_H2_PROXY_REPRICING_SKILL_P1Y"] = "NOT_TESTED"
        result = evaluate_gate(phase02, phase03, phase04)
        self.assertEqual(result["decision"], STOP)


if __name__ == "__main__":
    unittest.main()
