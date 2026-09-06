"""Strict configuration for the amended free one-year-proxy research."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .eiopa_rfr import G10_CURRENCIES


class ResearchConfigError(ValueError):
    """Raised when the registered research configuration is invalid."""


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    value_kind: str
    frequency: str


@dataclass(frozen=True)
class TargetInterval:
    effective_from: date
    midpoint: float


@dataclass(frozen=True)
class CurrencySpec:
    currency: str
    country: str
    ref_area: str
    headline: SeriesSpec
    underlying: SeriesSpec
    unemployment: SeriesSpec
    inflation_targets: tuple[TargetInterval, ...]

    def target_at(self, snapshot: date) -> float:
        eligible = [
            item.midpoint
            for item in self.inflation_targets
            if item.effective_from <= snapshot
        ]
        if not eligible:
            raise ResearchConfigError(
                f"No inflation target for {self.currency} at {snapshot}"
            )
        return eligible[-1]


@dataclass(frozen=True)
class BootstrapSpec:
    block_length_months: int
    resamples: int
    seed: int


@dataclass(frozen=True)
class ResearchConfig:
    schema_version: str
    namespace: str
    expectation_kind: str
    panel_start: date
    panel_end: date
    label_support_end: date
    evaluation_start: date
    evaluation_end: date
    sealed_start: date
    proxy_availability_lag_months: int
    minimum_zscore_months: int
    minimum_training_months_per_currency: int
    minimum_pooled_rows: int
    minimum_upstream_training_months_per_currency: int
    minimum_upstream_pooled_rows: int
    ridge_penalties: tuple[float, ...]
    bootstrap: BootstrapSpec
    currencies: dict[str, CurrencySpec]


def _series(raw: object, location: str) -> SeriesSpec:
    if not isinstance(raw, dict):
        raise ResearchConfigError(f"{location} must be an object")
    expected = {"series_id", "value_kind", "frequency"}
    if set(raw) != expected:
        raise ResearchConfigError(f"{location} fields mismatch")
    value_kind = str(raw["value_kind"])
    frequency = str(raw["frequency"])
    if value_kind not in {"index", "percent", "yoy_percent"}:
        raise ResearchConfigError(f"{location} has invalid value_kind")
    if frequency not in {"monthly", "quarterly"}:
        raise ResearchConfigError(f"{location} has invalid frequency")
    return SeriesSpec(str(raw["series_id"]), value_kind, frequency)


def _currencies(raw: object) -> dict[str, CurrencySpec]:
    if not isinstance(raw, dict) or set(raw) != G10_CURRENCIES:
        raise ResearchConfigError("currencies must contain exactly the G10 universe")
    result: dict[str, CurrencySpec] = {}
    for currency, item in raw.items():
        if not isinstance(item, dict):
            raise ResearchConfigError(f"currency {currency} must be an object")
        expected = {
            "country",
            "ref_area",
            "headline",
            "underlying",
            "unemployment",
            "inflation_targets",
        }
        if set(item) != expected:
            raise ResearchConfigError(f"currency {currency} fields mismatch")
        raw_targets = item["inflation_targets"]
        if not isinstance(raw_targets, list) or not raw_targets:
            raise ResearchConfigError(f"currency {currency} has no target intervals")
        targets = tuple(
            TargetInterval(
                effective_from=date.fromisoformat(str(target["effective_from"])),
                midpoint=float(target["midpoint"]),
            )
            for target in raw_targets
        )
        if tuple(sorted(targets, key=lambda value: value.effective_from)) != targets:
            raise ResearchConfigError(f"currency {currency} targets are not sorted")
        result[currency] = CurrencySpec(
            currency=currency,
            country=str(item["country"]),
            ref_area=str(item["ref_area"]),
            headline=_series(item["headline"], f"{currency}.headline"),
            underlying=_series(item["underlying"], f"{currency}.underlying"),
            unemployment=_series(item["unemployment"], f"{currency}.unemployment"),
            inflation_targets=targets,
        )
    return dict(sorted(result.items()))


def load_research_config(path: Path) -> ResearchConfig:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ResearchConfigError("research config must be an object")
    expected = {
        "schema_version",
        "namespace",
        "expectation_kind",
        "panel_start",
        "panel_end",
        "label_support_end",
        "evaluation_start",
        "evaluation_end",
        "sealed_start",
        "snapshot_timezone",
        "snapshot_local_time",
        "proxy_availability_lag_months",
        "minimum_zscore_months",
        "minimum_training_months_per_currency",
        "minimum_pooled_rows",
        "minimum_upstream_training_months_per_currency",
        "minimum_upstream_pooled_rows",
        "ridge_penalties",
        "bootstrap",
        "currencies",
    }
    if set(raw) != expected:
        raise ResearchConfigError(
            f"research config fields mismatch: {sorted(set(raw) ^ expected)}"
        )
    if raw["snapshot_timezone"] != "Europe/Brussels":
        raise ResearchConfigError("snapshot timezone contract changed")
    if raw["snapshot_local_time"] != "17:00:00":
        raise ResearchConfigError("snapshot time contract changed")
    bootstrap = raw["bootstrap"]
    if not isinstance(bootstrap, dict) or set(bootstrap) != {
        "kind",
        "block_length_months",
        "resamples",
        "seed",
    }:
        raise ResearchConfigError("bootstrap fields mismatch")
    if bootstrap["kind"] != "circular_moving_month_block":
        raise ResearchConfigError("bootstrap kind contract changed")
    config = ResearchConfig(
        schema_version=str(raw["schema_version"]),
        namespace=str(raw["namespace"]),
        expectation_kind=str(raw["expectation_kind"]),
        panel_start=date.fromisoformat(str(raw["panel_start"])),
        panel_end=date.fromisoformat(str(raw["panel_end"])),
        label_support_end=date.fromisoformat(str(raw["label_support_end"])),
        evaluation_start=date.fromisoformat(str(raw["evaluation_start"])),
        evaluation_end=date.fromisoformat(str(raw["evaluation_end"])),
        sealed_start=date.fromisoformat(str(raw["sealed_start"])),
        proxy_availability_lag_months=int(raw["proxy_availability_lag_months"]),
        minimum_zscore_months=int(raw["minimum_zscore_months"]),
        minimum_training_months_per_currency=int(
            raw["minimum_training_months_per_currency"]
        ),
        minimum_pooled_rows=int(raw["minimum_pooled_rows"]),
        minimum_upstream_training_months_per_currency=int(
            raw["minimum_upstream_training_months_per_currency"]
        ),
        minimum_upstream_pooled_rows=int(raw["minimum_upstream_pooled_rows"]),
        ridge_penalties=tuple(float(value) for value in raw["ridge_penalties"]),
        bootstrap=BootstrapSpec(
            block_length_months=int(bootstrap["block_length_months"]),
            resamples=int(bootstrap["resamples"]),
            seed=int(bootstrap["seed"]),
        ),
        currencies=_currencies(raw["currencies"]),
    )
    if not (
        config.panel_start
        <= config.evaluation_start
        <= config.evaluation_end
        <= config.panel_end
        < config.label_support_end
        < config.sealed_start
    ):
        raise ResearchConfigError("research date boundaries are invalid")
    if config.expectation_kind != "EIOPA_RFR_1Y_PROXY":
        raise ResearchConfigError("expectation kind contract changed")
    if sorted(set(config.ridge_penalties)) != list(config.ridge_penalties):
        raise ResearchConfigError("ridge penalties must be unique and sorted")
    if any(value <= 0 for value in config.ridge_penalties):
        raise ResearchConfigError("ridge penalties must be positive")
    return config
