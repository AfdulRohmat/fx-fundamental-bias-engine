"""Frozen Phase 04 FX transform and non-gating low-history diagnostics."""

from __future__ import annotations

import csv
import math
import random
import statistics
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from .artifacts import sha256_path, write_json, write_jsonl, write_manifest
from .research_config import ResearchConfig
from .time_utils import add_months, month_ends


def _fx_marks(
    path: Path, config: ResearchConfig
) -> tuple[dict[tuple[date, str], float], dict[date, date]]:
    daily: dict[date, dict[str, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            observation = date.fromisoformat(row["TIME_PERIOD"])
            if observation >= config.sealed_start:
                raise ValueError("ECB input reaches sealed data")
            daily.setdefault(observation, {})[str(row["CURRENCY"])] = float(
                row["OBS_VALUE"]
            )
    required = set(config.currencies) - {"EUR"}
    common_dates = sorted(
        observation
        for observation, values in daily.items()
        if set(values) == required
    )
    marks: dict[tuple[date, str], float] = {}
    source_dates: dict[date, date] = {}
    for snapshot in month_ends(config.panel_start, config.label_support_end):
        eligible = [value for value in common_dates if value <= snapshot]
        if not eligible:
            continue
        source_date = eligible[-1]
        source_dates[snapshot] = source_date
        marks[(snapshot, "EUR")] = 1.0
        for currency, value in daily[source_date].items():
            marks[(snapshot, currency)] = value
    return marks, source_dates


def _currency_returns(
    marks: dict[tuple[date, str], float], config: ResearchConfig
) -> dict[tuple[date, str], float]:
    result: dict[tuple[date, str], float] = {}
    currencies = tuple(config.currencies)
    for origin in month_ends(config.panel_start, config.panel_end):
        destination = add_months(origin, 1)
        if not all(
            (origin, currency) in marks and (destination, currency) in marks
            for currency in currencies
        ):
            continue
        versus_eur = {
            currency: -math.log(
                marks[(destination, currency)] / marks[(origin, currency)]
            )
            for currency in currencies
        }
        center = statistics.mean(versus_eur.values())
        for currency, value in versus_eur.items():
            result[(origin, currency)] = value - center
    return result


def _predictions(path: Path) -> dict[tuple[date, str], float | None]:
    result: dict[tuple[date, str], float | None] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (date.fromisoformat(row["snapshot"]), str(row["currency"]))
            raw = row["proxy_prediction_exploratory_bp"]
            result[key] = None if raw == "" else float(raw)
    return result


def _average_ranks(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: item[1])
    result: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for currency, _ in ordered[index:end]:
            result[currency] = rank
        index = end
    return result


def _correlation(left: list[float], right: list[float]) -> float:
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean)
        for x, y in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return 0.0 if denominator == 0 else numerator / denominator


def _slope(rows: list[dict[str, Any]]) -> float:
    x = [float(row["pair_pressure_bp"]) for row in rows]
    y = [float(row["pair_return_log"]) for row in rows]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0
    return sum(
        (left - x_mean) * (right - y_mean)
        for left, right in zip(x, y, strict=True)
    ) / denominator


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _bootstrap(
    rows: list[dict[str, Any]],
    *,
    statistic: Callable[[list[dict[str, Any]]], float],
    config: ResearchConfig,
    seed_offset: int,
) -> tuple[float, float]:
    by_date: dict[date, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(row["snapshot_date"], []).append(row)
    dates = sorted(by_date)
    if not dates:
        raise ValueError("Cannot bootstrap empty FX rows")
    generator = random.Random(config.bootstrap.seed + seed_offset)
    estimates: list[float] = []
    for _ in range(config.bootstrap.resamples):
        sampled_dates: list[date] = []
        while len(sampled_dates) < len(dates):
            start = generator.randrange(len(dates))
            sampled_dates.extend(
                dates[(start + offset) % len(dates)]
                for offset in range(config.bootstrap.block_length_months)
            )
        sample = [
            row
            for item_date in sampled_dates[: len(dates)]
            for row in by_date[item_date]
        ]
        estimates.append(statistic(sample))
    return _quantile(estimates, 0.025), _quantile(estimates, 0.975)


def _pair_rows(
    pressure: dict[tuple[date, str], float | None],
    returns: dict[tuple[date, str], float],
    config: ResearchConfig,
    *,
    excluded: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    currencies = tuple(
        currency for currency in config.currencies if currency not in excluded
    )
    rows: list[dict[str, Any]] = []
    for snapshot in month_ends(config.evaluation_start, config.evaluation_end):
        for left_index, base in enumerate(currencies):
            for quote in currencies[left_index + 1 :]:
                base_pressure = pressure.get((snapshot, base))
                quote_pressure = pressure.get((snapshot, quote))
                base_return = returns.get((snapshot, base))
                quote_return = returns.get((snapshot, quote))
                if None in (base_pressure, quote_pressure, base_return, quote_return):
                    continue
                assert base_pressure is not None
                assert quote_pressure is not None
                assert base_return is not None
                assert quote_return is not None
                rows.append(
                    {
                        "snapshot": snapshot.isoformat(),
                        "snapshot_date": snapshot,
                        "base": base,
                        "quote": quote,
                        "pair_pressure_bp": float(base_pressure)
                        - float(quote_pressure),
                        "pair_return_log": float(base_return) - float(quote_return),
                    }
                )
    return rows


def _monthly_rows(
    pressure: dict[tuple[date, str], float | None],
    returns: dict[tuple[date, str], float],
    config: ResearchConfig,
    *,
    excluded: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    currencies = tuple(
        currency for currency in config.currencies if currency not in excluded
    )
    rows: list[dict[str, Any]] = []
    for snapshot in month_ends(config.evaluation_start, config.evaluation_end):
        p = {currency: pressure.get((snapshot, currency)) for currency in currencies}
        r = {currency: returns.get((snapshot, currency)) for currency in currencies}
        if any(value is None for value in (*p.values(), *r.values())):
            continue
        clean_p: dict[str, float] = {}
        clean_r: dict[str, float] = {}
        for currency, value in p.items():
            assert value is not None
            clean_p[currency] = value
        for currency, value in r.items():
            assert value is not None
            clean_r[currency] = value
        p_ranks = _average_ranks(clean_p)
        r_ranks = _average_ranks(clean_r)
        ic = _correlation(
            [p_ranks[currency] for currency in currencies],
            [r_ranks[currency] for currency in currencies],
        )
        ordered = sorted(currencies, key=lambda currency: clean_p[currency])
        bottom = ordered[:2]
        top = ordered[-2:]
        boundary_tied = (
            clean_p[ordered[1]] == clean_p[ordered[2]]
            or clean_p[ordered[-2]] == clean_p[ordered[-3]]
        )
        if boundary_tied:
            continue
        spread = statistics.mean(
            clean_r[currency] for currency in top
        ) - statistics.mean(clean_r[currency] for currency in bottom)
        rows.append(
            {
                "snapshot": snapshot.isoformat(),
                "snapshot_date": snapshot,
                "rank_ic": ic,
                "extreme_spread_log": spread,
                "top_two": "+".join(sorted(top)),
                "bottom_two": "+".join(sorted(bottom)),
            }
        )
    return rows


def _diagnostics(
    pressure: dict[tuple[date, str], float | None],
    returns: dict[tuple[date, str], float],
    config: ResearchConfig,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    pairs = _pair_rows(pressure, returns, config)
    monthly = _monthly_rows(pressure, returns, config)
    pair_slope = _slope(pairs)
    pair_ci = _bootstrap(pairs, statistic=_slope, config=config, seed_offset=10)
    ic_mean = statistics.mean(float(row["rank_ic"]) for row in monthly)
    ic_ci = _bootstrap(
        monthly,
        statistic=lambda sample: statistics.mean(
            float(row["rank_ic"]) for row in sample
        ),
        config=config,
        seed_offset=20,
    )
    spread_mean = statistics.mean(
        float(row["extreme_spread_log"]) for row in monthly
    )
    spread_ci = _bootstrap(
        monthly,
        statistic=lambda sample: statistics.mean(
            float(row["extreme_spread_log"]) for row in sample
        ),
        config=config,
        seed_offset=30,
    )
    by_year = {}
    for year in (2021, 2022):
        year_pairs = [row for row in pairs if row["snapshot_date"].year == year]
        year_monthly = [row for row in monthly if row["snapshot_date"].year == year]
        by_year[str(year)] = {
            "pair_slope": _slope(year_pairs),
            "rank_ic": statistics.mean(float(row["rank_ic"]) for row in year_monthly),
            "spread_log": statistics.mean(
                float(row["extreme_spread_log"]) for row in year_monthly
            ),
        }
    leave_one_out = {}
    for currency in config.currencies:
        loo_pairs = _pair_rows(
            pressure, returns, config, excluded=frozenset({currency})
        )
        loo_monthly = _monthly_rows(
            pressure, returns, config, excluded=frozenset({currency})
        )
        leave_one_out[currency] = {
            "pair_slope": _slope(loo_pairs),
            "rank_ic": statistics.mean(
                float(row["rank_ic"]) for row in loo_monthly
            ),
            "spread_log": statistics.mean(
                float(row["extreme_spread_log"]) for row in loo_monthly
            ),
        }
    all_stable = all(
        value > 0
        for group in (*by_year.values(), *leave_one_out.values())
        for value in group.values()
    )
    result = {
        "pair_row_count": len(pairs),
        "pair_month_count": len({row["snapshot_date"] for row in pairs}),
        "full_g10_month_count": len(monthly),
        "pair_slope_log_return_per_bp": pair_slope,
        "pair_slope_95_ci": [*pair_ci],
        "mean_rank_ic": ic_mean,
        "mean_rank_ic_95_ci": [*ic_ci],
        "mean_extreme_spread_bp": spread_mean * 10_000.0,
        "mean_extreme_spread_95_ci_bp": [
            spread_ci[0] * 10_000.0,
            spread_ci[1] * 10_000.0,
        ],
        "by_year": by_year,
        "leave_one_currency_out": leave_one_out,
        "all_expected_signs_stable": all_stable,
    }
    return result, pairs, monthly


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_phase04(
    config: ResearchConfig,
    predictions_path: Path,
    ecb_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    marks, source_dates = _fx_marks(ecb_path, config)
    returns = _currency_returns(marks, config)
    pressure = _predictions(predictions_path)
    diagnostic, pairs, monthly = _diagnostics(pressure, returns, config)
    summary = {
        "phase": "04-currency-divergence",
        "status": "NOT_TESTED",
        "FB_H3_PAIR_DIRECTION_P1Y": "NOT_TESTED",
        "FB_H4_RANK_IC_P1Y": "NOT_TESTED",
        "FB_H5_EXTREME_SPREAD_P1Y": "NOT_TESTED",
        "FB_H6_STABILITY_P1Y": "NOT_TESTED",
        "reason": "No registered primary repricing predictions from Phase 03",
        "low_history_exploratory": diagnostic,
        "fx_marks_non_executable": True,
        "profitability_claim": False,
        "sealed_data_accessed": False,
    }
    _write_csv(output_dir / "pair_diagnostics.csv", pairs)
    _write_csv(output_dir / "monthly_rank_diagnostics.csv", monthly)
    write_json(output_dir / "summary.json", summary)
    write_json(
        output_dir / "sample_flow.json",
        {
            "ecb_monthly_marks": len(source_dates),
            "pair_rows": len(pairs),
            "full_g10_months": len(monthly),
        },
    )
    write_jsonl(output_dir / "issues.jsonl", [])
    write_json(output_dir / "config_snapshot.yaml", asdict(config))
    write_json(
        output_dir / "source_manifest.json",
        {
            "phase03_predictions_sha256": sha256_path(predictions_path),
            "ecb_fx_sha256": sha256_path(ecb_path),
            "research_marks_only": True,
        },
    )
    report = (
        "# Phase 04 - Currency divergence\n\n"
        "Registered status: `NOT_TESTED` for FB_H3 through FB_H6 because Phase "
        "03 produced no primary pressure.\n\n"
        f"The frozen low-history diagnostic covers {len(monthly)} complete G10 "
        f"months. Pair slope={diagnostic['pair_slope_log_return_per_bp']:.6g}; "
        f"rank IC={diagnostic['mean_rank_ic']:.3f}; mean extreme spread="
        f"{diagnostic['mean_extreme_spread_bp']:.1f} bp.\n\n"
        "ECB reference rates are non-executable research marks. There is no "
        "cost model, position sizing, trading rule, or profitability claim.\n"
    )
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    write_manifest(output_dir, phase="04-currency-divergence")
    return summary
