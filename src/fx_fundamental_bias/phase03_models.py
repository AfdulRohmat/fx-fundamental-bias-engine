"""Walk-forward policy and one-year-proxy repricing research."""

from __future__ import annotations

import csv
import json
import random
import statistics
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from .artifacts import sha256_path, write_json, write_jsonl, write_manifest
from .research_config import ResearchConfig
from .ridge import predict, ridge_fit
from .time_utils import add_months

MACRO_FEATURES = (
    "inflation_gap_z",
    "inflation_momentum_z",
    "labour_tightness_z",
    "labour_momentum_z",
)
POLICY_FEATURES = (*MACRO_FEATURES, "policy_rate_percent", "policy_change_3m_bp")
PROXY_FEATURES = (
    *MACRO_FEATURES,
    "pricing_gap_proxy_bp",
    "proxy_path_1y_bp",
    "proxy_change_1m_lag_bp",
)


def _read_panel(path: Path) -> list[dict[str, Any]]:
    numeric = {
        *MACRO_FEATURES,
        "policy_rate_percent",
        "policy_change_3m_bp",
        "policy_change_6m_bp",
        "proxy_path_1y_bp",
        "proxy_repricing_1m_bp",
    }
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            row["snapshot_date"] = date.fromisoformat(raw["snapshot"])
            for name in numeric:
                row[name] = None if raw.get(name, "") == "" else float(raw[name])
            row["panel_complete"] = raw["panel_complete"] == "True"
            rows.append(row)
    return rows


def _design(
    row: dict[str, Any], currencies: tuple[str, ...], features: tuple[str, ...]
) -> list[float]:
    return [float(row["currency"] == currency) for currency in currencies] + [
        float(row[name]) for name in features
    ]


def _has_values(row: dict[str, Any], names: tuple[str, ...]) -> bool:
    return all(row.get(name) is not None for name in names)


def _fit(
    rows: list[dict[str, Any]],
    *,
    currencies: tuple[str, ...],
    features: tuple[str, ...],
    target: str,
    penalty: float,
    nonnegative_feature_count: int = 0,
) -> tuple[float, ...]:
    design = [_design(row, currencies, features) for row in rows]
    outcomes = [float(row[target]) for row in rows]
    offset = len(currencies)
    return ridge_fit(
        design,
        outcomes,
        penalty=penalty,
        unpenalized=frozenset(range(offset)),
        nonnegative=frozenset(
            range(offset, offset + nonnegative_feature_count)
        ),
    )


def _select_penalty(
    rows: list[dict[str, Any]],
    *,
    config: ResearchConfig,
    features: tuple[str, ...],
    target: str,
    nonnegative_feature_count: int = 0,
) -> float:
    dates = sorted({row["snapshot_date"] for row in rows})
    if len(dates) < 12:
        return config.ridge_penalties[0]
    validation_dates = set(dates[-6:])
    inner = [row for row in rows if row["snapshot_date"] not in validation_dates]
    validation = [row for row in rows if row["snapshot_date"] in validation_dates]
    currencies = tuple(config.currencies)
    losses: list[tuple[float, float]] = []
    for penalty in config.ridge_penalties:
        coefficients = _fit(
            inner,
            currencies=currencies,
            features=features,
            target=target,
            penalty=penalty,
            nonnegative_feature_count=nonnegative_feature_count,
        )
        loss = statistics.mean(
            abs(
                float(row[target])
                - predict(_design(row, currencies, features), coefficients)
            )
            for row in validation
        )
        losses.append((loss, penalty))
    return min(losses)[1]


def _sample_ok(
    rows: list[dict[str, Any]],
    *,
    currencies: tuple[str, ...],
    minimum_per_currency: int,
    minimum_pooled: int,
) -> bool:
    counts = Counter(str(row["currency"]) for row in rows)
    return len(rows) >= minimum_pooled and all(
        counts[currency] >= minimum_per_currency for currency in currencies
    )


def _policy_walk_forward(
    rows: list[dict[str, Any]], config: ResearchConfig
) -> tuple[dict[tuple[date, str], dict[str, Any]], list[dict[str, Any]]]:
    currencies = tuple(config.currencies)
    dates = sorted({row["snapshot_date"] for row in rows})
    output: dict[tuple[date, str], dict[str, Any]] = {}
    coefficients_output: list[dict[str, Any]] = []
    for origin in dates:
        training = [
            row
            for row in rows
            if add_months(row["snapshot_date"], 6) <= origin
            and _has_values(row, (*POLICY_FEATURES, "policy_change_6m_bp"))
        ]
        upstream_ok = _sample_ok(
            training,
            currencies=currencies,
            minimum_per_currency=config.minimum_upstream_training_months_per_currency,
            minimum_pooled=config.minimum_upstream_pooled_rows,
        )
        primary_ok = _sample_ok(
            training,
            currencies=currencies,
            minimum_per_currency=config.minimum_training_months_per_currency,
            minimum_pooled=config.minimum_pooled_rows,
        )
        constrained: tuple[float, ...] | None = None
        selected: float | None = None
        if upstream_ok:
            selected = _select_penalty(
                training,
                config=config,
                features=POLICY_FEATURES,
                target="policy_change_6m_bp",
                nonnegative_feature_count=4,
            )
            constrained = _fit(
                training,
                currencies=currencies,
                features=POLICY_FEATURES,
                target="policy_change_6m_bp",
                penalty=selected,
                nonnegative_feature_count=4,
            )
            unconstrained = _fit(
                training,
                currencies=currencies,
                features=POLICY_FEATURES,
                target="policy_change_6m_bp",
                penalty=selected,
            )
            for model_name, values in (
                ("policy_constrained", constrained),
                ("policy_unconstrained", unconstrained),
            ):
                coefficients_output.append(
                    {
                        "origin": origin.isoformat(),
                        "model": model_name,
                        "penalty": selected,
                        "training_rows": len(training),
                        "coefficients": list(values),
                    }
                )
        equal_coefficients: tuple[float, ...] | None = None
        if primary_ok:
            equal_rows = []
            for row in training:
                candidate = dict(row)
                candidate["equal_macro"] = statistics.mean(
                    float(row[name]) for name in MACRO_FEATURES
                )
                equal_rows.append(candidate)
            equal_features = (
                "equal_macro",
                "policy_rate_percent",
                "policy_change_3m_bp",
            )
            equal_penalty = _select_penalty(
                equal_rows,
                config=config,
                features=equal_features,
                target="policy_change_6m_bp",
                nonnegative_feature_count=1,
            )
            equal_coefficients = _fit(
                equal_rows,
                currencies=currencies,
                features=equal_features,
                target="policy_change_6m_bp",
                penalty=equal_penalty,
                nonnegative_feature_count=1,
            )
        for row in (item for item in rows if item["snapshot_date"] == origin):
            result = {
                "structural_policy_change_6m_bp": None,
                "policy_prediction_primary_bp": None,
                "policy_prediction_equal_weight_bp": None,
                "policy_penalty": selected,
                "policy_training_rows": len(training),
            }
            if constrained is not None and _has_values(row, POLICY_FEATURES):
                prediction = predict(
                    _design(row, currencies, POLICY_FEATURES), constrained
                )
                result["structural_policy_change_6m_bp"] = prediction
                if primary_ok:
                    result["policy_prediction_primary_bp"] = prediction
            if equal_coefficients is not None and _has_values(row, POLICY_FEATURES):
                equal_row = dict(row)
                equal_row["equal_macro"] = statistics.mean(
                    float(row[name]) for name in MACRO_FEATURES
                )
                result["policy_prediction_equal_weight_bp"] = predict(
                    _design(
                        equal_row,
                        currencies,
                        ("equal_macro", "policy_rate_percent", "policy_change_3m_bp"),
                    ),
                    equal_coefficients,
                )
            output[(origin, str(row["currency"]))] = result
    return output, coefficients_output


def _proxy_walk_forward(
    rows: list[dict[str, Any]],
    policy: dict[tuple[date, str], dict[str, Any]],
    config: ResearchConfig,
) -> tuple[dict[tuple[date, str], dict[str, Any]], list[dict[str, Any]]]:
    currencies = tuple(config.currencies)
    dates = sorted({row["snapshot_date"] for row in rows})
    proxy_by_key = {
        (row["snapshot_date"], str(row["currency"])): row["proxy_path_1y_bp"]
        for row in rows
    }
    enriched: list[dict[str, Any]] = []
    for row in rows:
        candidate = dict(row)
        key = (row["snapshot_date"], str(row["currency"]))
        structural = policy[key]["structural_policy_change_6m_bp"]
        candidate["pricing_gap_proxy_bp"] = (
            None
            if structural is None or row["proxy_path_1y_bp"] is None
            else structural - row["proxy_path_1y_bp"]
        )
        previous = proxy_by_key.get(
            (add_months(row["snapshot_date"], -1), str(row["currency"]))
        )
        candidate["proxy_change_1m_lag_bp"] = (
            None
            if previous is None or row["proxy_path_1y_bp"] is None
            else row["proxy_path_1y_bp"] - previous
        )
        enriched.append(candidate)
    output: dict[tuple[date, str], dict[str, Any]] = {}
    coefficients_output: list[dict[str, Any]] = []
    for origin in dates:
        training = [
            row
            for row in enriched
            if add_months(row["snapshot_date"], 1) <= origin
            and _has_values(row, (*PROXY_FEATURES, "proxy_repricing_1m_bp"))
        ]
        primary_ok = _sample_ok(
            training,
            currencies=currencies,
            minimum_per_currency=config.minimum_training_months_per_currency,
            minimum_pooled=config.minimum_pooled_rows,
        )
        diagnostic_ok = _sample_ok(
            training,
            currencies=currencies,
            minimum_per_currency=config.minimum_upstream_training_months_per_currency,
            minimum_pooled=config.minimum_upstream_pooled_rows,
        )
        selected: float | None = None
        coefficients: tuple[float, ...] | None = None
        if diagnostic_ok:
            selected = _select_penalty(
                training,
                config=config,
                features=PROXY_FEATURES,
                target="proxy_repricing_1m_bp",
            )
            coefficients = _fit(
                training,
                currencies=currencies,
                features=PROXY_FEATURES,
                target="proxy_repricing_1m_bp",
                penalty=selected,
            )
            coefficients_output.append(
                {
                    "origin": origin.isoformat(),
                    "model": "proxy_repricing",
                    "penalty": selected,
                    "training_rows": len(training),
                    "coefficients": list(coefficients),
                }
            )
        for row in (item for item in enriched if item["snapshot_date"] == origin):
            prediction = None
            if coefficients is not None and _has_values(row, PROXY_FEATURES):
                prediction = predict(
                    _design(row, currencies, PROXY_FEATURES), coefficients
                )
            output[(origin, str(row["currency"]))] = {
                "currency_pressure_bp": prediction if primary_ok else None,
                "proxy_prediction_bp": prediction if primary_ok else None,
                "proxy_prediction_exploratory_bp": prediction,
                "proxy_momentum_benchmark_bp": row["proxy_change_1m_lag_bp"],
                "pricing_gap_proxy_bp": row["pricing_gap_proxy_bp"],
                "proxy_penalty": selected,
                "proxy_training_rows": len(training),
            }
    return output, coefficients_output


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def block_bootstrap_ci(
    values_by_date: dict[date, list[float]],
    *,
    block_length: int,
    resamples: int,
    seed: int,
) -> tuple[float, float]:
    dates = sorted(values_by_date)
    monthly = [statistics.mean(values_by_date[item]) for item in dates]
    if not monthly:
        raise ValueError("Cannot bootstrap an empty result")
    generator = random.Random(seed)
    estimates: list[float] = []
    for _ in range(resamples):
        sample: list[float] = []
        while len(sample) < len(monthly):
            start = generator.randrange(len(monthly))
            sample.extend(
                monthly[(start + offset) % len(monthly)]
                for offset in range(block_length)
            )
        estimates.append(statistics.mean(sample[: len(monthly)]))
    return _quantile(estimates, 0.025), _quantile(estimates, 0.975)


def _metric(
    rows: list[dict[str, Any]],
    *,
    target: str,
    model: str,
    benchmarks: tuple[str, str],
    config: ResearchConfig,
) -> dict[str, Any]:
    eligible = [
        row
        for row in rows
        if config.evaluation_start <= row["snapshot_date"] <= config.evaluation_end
        and _has_values(row, (target, model, *benchmarks))
    ]
    if not eligible:
        return {"estimable": False, "row_count": 0, "supported": False}
    losses = {
        name: statistics.mean(
            abs(float(row[target]) - float(row[name])) for row in eligible
        )
        for name in (model, *benchmarks)
    }
    intervals: dict[str, list[float]] = {}
    for index, benchmark in enumerate(benchmarks):
        paired: dict[date, list[float]] = {}
        for row in eligible:
            improvement = abs(float(row[target]) - float(row[benchmark])) - abs(
                float(row[target]) - float(row[model])
            )
            paired.setdefault(row["snapshot_date"], []).append(improvement)
        interval = block_bootstrap_ci(
            paired,
            block_length=config.bootstrap.block_length_months,
            resamples=config.bootstrap.resamples,
            seed=config.bootstrap.seed + index,
        )
        intervals[benchmark] = [*interval]
    supported = all(losses[model] < losses[name] for name in benchmarks) and all(
        interval[0] > 0 for interval in intervals.values()
    )
    return {
        "estimable": True,
        "row_count": len(eligible),
        "month_count": len({row["snapshot_date"] for row in eligible}),
        "mae": losses,
        "paired_improvement_95_ci": intervals,
        "supported": supported,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_phase03(
    config: ResearchConfig,
    panel_path: Path,
    phase02_summary_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    rows = _read_panel(panel_path)
    policy, policy_coefficients = _policy_walk_forward(rows, config)
    proxy, proxy_coefficients = _proxy_walk_forward(rows, policy, config)
    predictions: list[dict[str, Any]] = []
    for row in rows:
        key = (row["snapshot_date"], str(row["currency"]))
        predictions.append(
            {
                "snapshot": row["snapshot"],
                "snapshot_date": row["snapshot_date"],
                "currency": row["currency"],
                "policy_change_6m_bp": row["policy_change_6m_bp"],
                "proxy_repricing_1m_bp": row["proxy_repricing_1m_bp"],
                "proxy_path_1y_bp": row["proxy_path_1y_bp"],
                **policy[key],
                **proxy[key],
            }
        )
    for row in predictions:
        row["policy_no_change_bp"] = 0.0
        row["proxy_no_change_bp"] = 0.0
    h1 = _metric(
        predictions,
        target="policy_change_6m_bp",
        model="policy_prediction_primary_bp",
        benchmarks=("policy_no_change_bp", "policy_prediction_equal_weight_bp"),
        config=config,
    )
    h2 = _metric(
        predictions,
        target="proxy_repricing_1m_bp",
        model="proxy_prediction_bp",
        benchmarks=("proxy_no_change_bp", "proxy_momentum_benchmark_bp"),
        config=config,
    )
    h2_exploratory = _metric(
        predictions,
        target="proxy_repricing_1m_bp",
        model="proxy_prediction_exploratory_bp",
        benchmarks=("proxy_no_change_bp", "proxy_momentum_benchmark_bp"),
        config=config,
    )
    phase02_summary = json.loads(phase02_summary_path.read_text(encoding="utf-8"))
    panel_quality_pass = phase02_summary["status"] == "PASS"
    h1_status = "SUPPORTED" if h1.get("supported") else "NOT_SUPPORTED"
    h2_status = "SUPPORTED" if h2.get("supported") else "NOT_SUPPORTED"
    if not panel_quality_pass:
        h1_status = h2_status = "NOT_TESTED"
    summary = {
        "phase": "03-policy-proxy-models",
        "status": "PASS" if panel_quality_pass else "REVIEW_REQUIRED",
        "FB_H1_POLICY_SKILL_P1Y": h1_status,
        "FB_H2_PROXY_REPRICING_SKILL_P1Y": h2_status,
        "h1_diagnostic": h1,
        "h2_diagnostic": h2,
        "h2_low_history_exploratory": h2_exploratory,
        "panel_quality_pass": panel_quality_pass,
        "fx_outcomes_accessed": False,
        "sealed_data_accessed": False,
        "prediction_rows": len(predictions),
    }
    _write_csv(output_dir / "predictions.csv", predictions)
    write_json(
        output_dir / "coefficients.json", policy_coefficients + proxy_coefficients
    )
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "sample_flow.json", {"panel_rows": len(rows)})
    write_jsonl(output_dir / "issues.jsonl", [])
    write_json(output_dir / "config_snapshot.yaml", asdict(config))
    write_json(
        output_dir / "source_manifest.json",
        {"panel_sha256": sha256_path(panel_path), "fx_outcomes_accessed": False},
    )
    report = (
        "# Phase 03 - Policy and proxy models\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"FB_H1: `{h1_status}`; diagnostic support={h1.get('supported')}.\n\n"
        f"FB_H2: `{h2_status}`; diagnostic support={h2.get('supported')}.\n\n"
        "All folds are past-only and label-purged. The quality status remains "
        "conditional on Phase 02 coverage. No FX outcome was loaded.\n"
    )
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    write_manifest(output_dir, phase="03-policy-proxy-models")
    return summary
