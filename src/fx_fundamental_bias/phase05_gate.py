"""Fail-closed Phase 05 aggregation; no refitting or new outcomes."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .artifacts import sha256_path, write_json, write_jsonl, write_manifest
from .research_config import ResearchConfig

PROCEED = "PROCEED_TO_TECHNICAL_TIMING_RESEARCH_P1Y_PROXY"
STOP = "DO_NOT_PROCEED_WITH_P1Y_PROXY_SPECIFICATION"


def _load(path: Path, phase: str) -> dict[str, Any]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("phase") != phase:
        raise ValueError(f"Unexpected or malformed {phase} summary")
    return value


def evaluate_gate(
    phase02: dict[str, Any], phase03: dict[str, Any], phase04: dict[str, Any]
) -> dict[str, Any]:
    fx_family = (
        phase04.get("FB_H3_PAIR_DIRECTION_P1Y"),
        phase04.get("FB_H4_RANK_IC_P1Y"),
        phase04.get("FB_H5_EXTREME_SPREAD_P1Y"),
    )
    supported_fx = sum(value == "SUPPORTED" for value in fx_family)
    gates = [
        {
            "gate": "point_in_time_and_provenance",
            "passed": phase02.get("status") == "PASS",
            "evidence": phase02.get("status"),
        },
        {
            "gate": "full_g10_evaluation_coverage",
            "passed": phase02.get("evaluation_complete_row_count")
            == phase02.get("evaluation_row_count"),
            "evidence": (
                f"{phase02.get('evaluation_complete_row_count')}/"
                f"{phase02.get('evaluation_row_count')} rows"
            ),
        },
        {
            "gate": "FB_H1_POLICY_SKILL_P1Y",
            "passed": phase03.get("FB_H1_POLICY_SKILL_P1Y") == "SUPPORTED",
            "evidence": phase03.get("FB_H1_POLICY_SKILL_P1Y"),
        },
        {
            "gate": "FB_H2_PROXY_REPRICING_SKILL_P1Y",
            "passed": phase03.get("FB_H2_PROXY_REPRICING_SKILL_P1Y")
            == "SUPPORTED",
            "evidence": phase03.get("FB_H2_PROXY_REPRICING_SKILL_P1Y"),
        },
        {
            "gate": "at_least_two_fx_tests_including_H3_or_H4",
            "passed": supported_fx >= 2
            and any(value == "SUPPORTED" for value in fx_family[:2]),
            "evidence": list(fx_family),
        },
        {
            "gate": "FB_H6_STABILITY_P1Y",
            "passed": phase04.get("FB_H6_STABILITY_P1Y") == "SUPPORTED",
            "evidence": phase04.get("FB_H6_STABILITY_P1Y"),
        },
        {
            "gate": "non_executable_fx_and_no_profitability_claim",
            "passed": phase04.get("fx_marks_non_executable") is True
            and phase04.get("profitability_claim") is False,
            "evidence": {
                "fx_marks_non_executable": phase04.get("fx_marks_non_executable"),
                "profitability_claim": phase04.get("profitability_claim"),
            },
        },
        {
            "gate": "sealed_2025_plus",
            "passed": all(
                phase.get("sealed_data_accessed") is False
                for phase in (phase02, phase03, phase04)
            ),
            "evidence": "sealed_data_accessed=false in phases 02-04",
        },
    ]
    decision = PROCEED if all(item["passed"] for item in gates) else STOP
    return {
        "phase": "05-research-gate",
        "decision": decision,
        "passed_gate_count": sum(bool(item["passed"]) for item in gates),
        "gate_count": len(gates),
        "gates": gates,
        "original_tier_a_six_month_specification": "NOT_TESTED",
        "sealed_data_accessed": False,
    }


def build_phase05(
    config: ResearchConfig,
    phase02_path: Path,
    phase03_path: Path,
    phase04_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    phase02 = _load(phase02_path, "02-canonical-panel")
    phase03 = _load(phase03_path, "03-policy-proxy-models")
    phase04 = _load(phase04_path, "04-currency-divergence")
    result = evaluate_gate(phase02, phase03, phase04)
    write_json(output_dir / "summary.json", result)
    write_json(
        output_dir / "sample_flow.json",
        {
            "phase02_evaluation_rows": phase02["evaluation_row_count"],
            "phase02_complete_rows": phase02["evaluation_complete_row_count"],
            "phase03_prediction_rows": phase03["prediction_rows"],
            "phase04_exploratory_full_g10_months": phase04[
                "low_history_exploratory"
            ]["full_g10_month_count"],
        },
    )
    write_jsonl(output_dir / "issues.jsonl", [])
    write_json(output_dir / "config_snapshot.yaml", asdict(config))
    write_json(
        output_dir / "source_manifest.json",
        {
            "phase02_summary_sha256": sha256_path(phase02_path),
            "phase03_summary_sha256": sha256_path(phase03_path),
            "phase04_summary_sha256": sha256_path(phase04_path),
            "refit_performed": False,
            "new_outcomes_read": False,
        },
    )
    failures = [item for item in result["gates"] if not item["passed"]]
    report = (
        "# Phase 05 - Fundamental Bias research gate\n\n"
        f"Decision: `{result['decision']}`\n\n"
        f"Only {result['passed_gate_count']}/{result['gate_count']} mandatory "
        f"gates passed; {len(failures)} failed. Phase 05 performed no refit and "
        "read no new outcome. The original Tier A six-month specification remains "
        "`NOT_TESTED`.\n"
    )
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    write_manifest(output_dir, phase="05-research-gate")
    return result
