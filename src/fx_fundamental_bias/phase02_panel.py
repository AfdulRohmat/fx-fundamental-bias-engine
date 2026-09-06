"""Build the amended monthly G10 panel without reading FX outcomes."""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .alfred import VintageTable, load_series
from .artifacts import sha256_path, write_json, write_jsonl, write_manifest
from .eiopa_rfr import parse_term_structures
from .research_config import CurrencySpec, ResearchConfig
from .time_utils import add_months, month_end, month_ends


@dataclass(frozen=True)
class FeatureValue:
    raw: float | None
    z: float | None
    reference_period: date | None


def _policy_rates(path: Path) -> dict[tuple[str, date], float]:
    result: dict[tuple[str, date], float] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            period = date.fromisoformat(f"{row['TIME_PERIOD']}-01")
            key = (str(row["REF_AREA"]), month_end(period.year, period.month))
            value = float(row["OBS_VALUE"])
            if key in result:
                raise ValueError(f"Duplicate BIS policy observation: {key}")
            result[key] = value
    return result


def _curve_rates(raw_root: Path) -> dict[tuple[str, date], tuple[float, str]]:
    result: dict[tuple[str, date], tuple[float, str]] = {}
    for path in sorted((raw_root / "eiopa").glob("*.zip")):
        for point in parse_term_structures(path):
            key = (point.currency, point.reference_date)
            value = (point.rate_percent, point.source_instrument)
            if key in result and result[key] != value:
                raise ValueError(f"Conflicting EIOPA curve: {key}")
            result[key] = value
    return result


def _series_observations(
    table: VintageTable, vintage: date
) -> list[tuple[date, float]]:
    return [
        (observation, table.values[(observation, vintage)])
        for observation in table.observation_dates(vintage)
    ]


def _yoy_values(
    observations: list[tuple[date, float]], *, value_kind: str
) -> list[tuple[date, float]]:
    if value_kind == "yoy_percent":
        return observations
    indexed = {item_date: value for item_date, value in observations}
    result: list[tuple[date, float]] = []
    for item_date, value in observations:
        previous_month = add_months(item_date, -12)
        previous = indexed.get(date(previous_month.year, previous_month.month, 1))
        if previous is not None and previous > 0:
            result.append((item_date, 100.0 * (value / previous - 1.0)))
    return result


def _zscore(items: list[tuple[date, float]], index: int, minimum: int) -> float | None:
    history = [value for _, value in items[:index]]
    if len(history) < minimum:
        return None
    deviation = statistics.stdev(history)
    if deviation == 0:
        return None
    return (items[index][1] - statistics.mean(history)) / deviation


def _latest_feature(
    items: list[tuple[date, float]],
    *,
    snapshot: date,
    frequency: str,
    minimum: int,
) -> FeatureValue:
    eligible = [index for index, item in enumerate(items) if item[0] <= snapshot]
    if not eligible:
        return FeatureValue(None, None, None)
    index = eligible[-1]
    reference_period, raw = items[index]
    maximum_age = 6 if frequency == "monthly" else 9
    threshold = add_months(snapshot, -maximum_age)
    if reference_period < date(threshold.year, threshold.month, 1):
        return FeatureValue(None, None, reference_period)
    return FeatureValue(raw, _zscore(items, index, minimum), reference_period)


def _feature_sequences(
    table: VintageTable,
    *,
    vintage: date,
    value_kind: str,
) -> tuple[list[tuple[date, float]], list[tuple[date, float]]]:
    levels = _yoy_values(
        _series_observations(table, vintage), value_kind=value_kind
    )
    by_date = {item_date: value for item_date, value in levels}
    momentum = []
    for index, (item_date, value) in enumerate(levels):
        previous_month = add_months(item_date, -3)
        previous = by_date.get(date(previous_month.year, previous_month.month, 1))
        if previous is None and index > 0:
            previous = levels[index - 1][1]
        if previous is not None:
            momentum.append((item_date, value - previous))
    return levels, momentum


def _target_midpoint(spec: CurrencySpec, snapshot: date) -> float:
    eligible = [
        item for item in spec.inflation_targets if item.effective_from <= snapshot
    ]
    if not eligible:
        raise ValueError(f"No inflation target for {spec.currency}/{snapshot}")
    return eligible[-1].midpoint


def _dominance(row: dict[str, Any]) -> str:
    inflation = (row["inflation_gap_z"], row["inflation_momentum_z"])
    labour = (row["labour_tightness_z"], row["labour_momentum_z"])
    if any(value is None for value in (*inflation, *labour)):
        return "INCOMPLETE"
    inflation_sign = 1 if min(inflation) > 0 else -1 if max(inflation) < 0 else 0
    labour_sign = 1 if min(labour) > 0 else -1 if max(labour) < 0 else 0
    if inflation_sign == labour_sign == 1:
        return "HAWKISH"
    if inflation_sign == labour_sign == -1:
        return "DOVISH"
    return "MIXED"


def _build_row(
    *,
    snapshot: date,
    spec: CurrencySpec,
    tables: dict[str, VintageTable],
    policies: dict[tuple[str, date], float],
    curves: dict[tuple[str, date], tuple[float, str]],
    minimum: int,
) -> dict[str, Any]:
    headline, _ = _feature_sequences(
        tables[spec.headline.series_id],
        vintage=snapshot,
        value_kind=spec.headline.value_kind,
    )
    _, underlying_momentum = _feature_sequences(
        tables[spec.underlying.series_id],
        vintage=snapshot,
        value_kind=spec.underlying.value_kind,
    )
    unemployment = _series_observations(tables[spec.unemployment.series_id], snapshot)
    labour_tightness = [(item_date, -value) for item_date, value in unemployment]
    labour_momentum = []
    for index, (item_date, value) in enumerate(unemployment):
        if index >= 3:
            labour_momentum.append((item_date, -(value - unemployment[index - 3][1])))
    gap_sequence = [
        (item_date, value - _target_midpoint(spec, item_date))
        for item_date, value in headline
    ]
    features = {
        "inflation_gap": _latest_feature(
            gap_sequence,
            snapshot=snapshot,
            frequency=spec.headline.frequency,
            minimum=minimum,
        ),
        "inflation_momentum": _latest_feature(
            underlying_momentum,
            snapshot=snapshot,
            frequency=spec.underlying.frequency,
            minimum=minimum,
        ),
        "labour_tightness": _latest_feature(
            labour_tightness,
            snapshot=snapshot,
            frequency=spec.unemployment.frequency,
            minimum=minimum,
        ),
        "labour_momentum": _latest_feature(
            labour_momentum,
            snapshot=snapshot,
            frequency=spec.unemployment.frequency,
            minimum=minimum,
        ),
    }
    policy = policies.get((spec.ref_area, snapshot))
    policy_6m = policies.get((spec.ref_area, add_months(snapshot, 6)))
    policy_3m_ago = policies.get((spec.ref_area, add_months(snapshot, -3)))
    eligible_curve_period = add_months(snapshot, -1)
    curve = curves.get((spec.currency, eligible_curve_period))
    next_policy = policies.get((spec.ref_area, add_months(snapshot, 1)))
    next_curve = curves.get((spec.currency, snapshot))
    row: dict[str, Any] = {
        "snapshot": snapshot.isoformat(),
        "currency": spec.currency,
        "country": spec.country,
        "macro_vintage": snapshot.isoformat(),
        "policy_rate_percent": policy,
        "policy_change_3m_bp": None
        if policy is None or policy_3m_ago is None
        else 100.0 * (policy - policy_3m_ago),
        "policy_change_6m_bp": None
        if policy is None or policy_6m is None
        else 100.0 * (policy_6m - policy),
        "rfr_reference_period": eligible_curve_period.isoformat(),
        "rfr_1y_percent": None if curve is None else curve[0],
        "rfr_source_instrument": None if curve is None else curve[1],
        "proxy_path_1y_bp": None
        if curve is None or policy is None
        else 100.0 * (curve[0] - policy),
    }
    next_proxy_path = (
        None
        if next_curve is None or next_policy is None
        else 100.0 * (next_curve[0] - next_policy)
    )
    row["proxy_repricing_1m_bp"] = (
        None
        if row["proxy_path_1y_bp"] is None or next_proxy_path is None
        else next_proxy_path - row["proxy_path_1y_bp"]
    )
    for name, feature in features.items():
        row[f"{name}_raw"] = feature.raw
        row[f"{name}_z"] = feature.z
        row[f"{name}_reference_period"] = (
            None
            if feature.reference_period is None
            else feature.reference_period.isoformat()
        )
    row["macro_complete"] = all(
        row[f"{name}_z"] is not None for name in features
    )
    row["panel_complete"] = bool(
        row["macro_complete"]
        and policy is not None
        and row["policy_change_6m_bp"] is not None
        and row["proxy_path_1y_bp"] is not None
    )
    row["dominance_regime"] = _dominance(row)
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_phase02(
    config: ResearchConfig, raw_root: Path, output_dir: Path
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    series_ids = {
        series.series_id
        for spec in config.currencies.values()
        for series in (spec.headline, spec.underlying, spec.unemployment)
    }
    tables = {
        series_id: load_series(raw_root / "alfred", series_id)
        for series_id in sorted(series_ids)
    }
    policies = _policy_rates(raw_root / "bis" / "policy_rates_monthly.csv")
    curves = _curve_rates(raw_root)
    rows = [
        _build_row(
            snapshot=snapshot,
            spec=spec,
            tables=tables,
            policies=policies,
            curves=curves,
            minimum=config.minimum_zscore_months,
        )
        for snapshot in month_ends(config.panel_start, config.panel_end)
        for spec in config.currencies.values()
    ]
    _write_csv(output_dir / "panel.csv", rows)
    source_manifest = {
        "alfred_series": len(series_ids),
        "bis_sha256": sha256_path(raw_root / "bis" / "policy_rates_monthly.csv"),
        "eiopa_archives": len(tuple((raw_root / "eiopa").glob("*.zip"))),
        "sealed_data_accessed": False,
    }
    write_json(output_dir / "source_manifest.json", source_manifest)
    complete = [row for row in rows if row["panel_complete"]]
    by_currency = {
        currency: sum(
            bool(row["panel_complete"])
            for row in rows
            if row["currency"] == currency
        )
        for currency in config.currencies
    }
    instruments = Counter(
        str(row["rfr_source_instrument"])
        for row in rows
        if row["rfr_source_instrument"] is not None
    )
    evaluation = [
        row
        for row in rows
        if config.evaluation_start <= date.fromisoformat(row["snapshot"])
        <= config.evaluation_end
    ]
    evaluation_complete = sum(bool(row["panel_complete"]) for row in evaluation)
    quality_pass = evaluation_complete == len(evaluation)
    summary = {
        "phase": "02-canonical-panel",
        "status": "PASS" if quality_pass else "REVIEW_REQUIRED",
        "row_count": len(rows),
        "complete_row_count": len(complete),
        "evaluation_row_count": len(evaluation),
        "evaluation_complete_row_count": evaluation_complete,
        "complete_months_by_currency": by_currency,
        "rfr_instruments": dict(sorted(instruments.items())),
        "point_in_time_macro": True,
        "proxy_availability_lag_months": config.proxy_availability_lag_months,
        "known_limitation": (
            "Retired ALFRED OECD series can become stale before 2022-12; "
            "recency checks fail those rows closed."
        ),
        "sealed_data_accessed": False,
    }
    write_json(output_dir / "sample_flow.json", summary)
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "issues.jsonl", [])
    write_json(output_dir / "config_snapshot.yaml", asdict(config))
    report = (
        "# Phase 02 - Canonical panel\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Built {len(rows)} country-month rows; {len(complete)} are complete. "
        f"The registered evaluation slice has {evaluation_complete}/{len(evaluation)} "
        "complete rows. Macro values are selected from the exact month-end ALFRED "
        "vintage, and EIOPA curves enter only after the frozen one-month lag.\n\n"
        "The panel deliberately fails stale retired series closed. No FX outcome "
        "was parsed by this phase.\n"
    )
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    write_manifest(output_dir, phase="02-canonical-panel")
    return summary
