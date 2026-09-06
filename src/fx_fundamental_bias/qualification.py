"""Strict source-catalog validation and Phase 01 matrix generation."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .eiopa_rfr import G10_CURRENCIES

REQUIRED_FEATURES = frozenset(
    {
        "headline_inflation",
        "underlying_inflation",
        "unemployment",
        "policy_rate",
        "policy_expectation_6m",
        "central_bank_profile",
        "fx_reference",
    }
)
DECISIONS = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED"})
REF_AREA_BY_CURRENCY = {
    "AUD": "AU",
    "CAD": "CA",
    "CHF": "CH",
    "EUR": "XM",
    "GBP": "GB",
    "JPY": "JP",
    "NOK": "NO",
    "NZD": "NZ",
    "SEK": "SE",
    "USD": "US",
}
FIELDS = (
    "currency",
    "feature",
    "provider",
    "series_id",
    "frequency",
    "coverage_start",
    "coverage_end",
    "publication_time_status",
    "vintage_status",
    "expectation_kind",
    "license_status",
    "missing_rate",
    "decision",
    "limitation",
)


class QualificationError(ValueError):
    """Raised when the Phase 01 source catalog is incomplete or inconsistent."""


def load_catalog(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if rows is None:
        rows = _expand_feature_sources(document.get("feature_sources"))
    if not isinstance(rows, list) or not rows:
        raise QualificationError("Source catalog must contain a non-empty rows list")
    parsed: list[dict[str, Any]] = []
    keys: set[tuple[str, str]] = set()
    for number, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            raise QualificationError(f"row {number}: expected an object")
        unknown = set(raw) - set(FIELDS)
        missing = set(FIELDS) - set(raw)
        if unknown or missing:
            raise QualificationError(
                f"row {number}: fields mismatch; missing={sorted(missing)} "
                f"unknown={sorted(unknown)}"
            )
        row = dict(raw)
        currency = str(row["currency"])
        feature = str(row["feature"])
        decision = str(row["decision"])
        if currency not in G10_CURRENCIES:
            raise QualificationError(f"row {number}: invalid currency {currency}")
        if feature not in REQUIRED_FEATURES:
            raise QualificationError(f"row {number}: invalid feature {feature}")
        if decision not in DECISIONS:
            raise QualificationError(f"row {number}: invalid decision {decision}")
        key = (currency, feature)
        if key in keys:
            raise QualificationError(f"row {number}: duplicate key {key}")
        keys.add(key)
        parsed.append(row)
    expected = {
        (currency, feature)
        for currency in G10_CURRENCIES
        for feature in REQUIRED_FEATURES
    }
    if keys != expected:
        raise QualificationError(
            f"Source catalog key mismatch; missing={sorted(expected - keys)} "
            f"unexpected={sorted(keys - expected)}"
        )
    return sorted(parsed, key=lambda row: (row["currency"], row["feature"]))


def _expand_feature_sources(raw_sources: object) -> list[dict[str, Any]]:
    if not isinstance(raw_sources, dict):
        raise QualificationError(
            "Source catalog requires rows or a feature_sources object"
        )
    rows: list[dict[str, Any]] = []
    for feature, raw_source in raw_sources.items():
        if not isinstance(raw_source, dict):
            raise QualificationError(f"feature {feature}: expected an object")
        defaults = raw_source.get("defaults")
        currencies = raw_source.get("currencies")
        if not isinstance(defaults, dict) or not isinstance(currencies, dict):
            raise QualificationError(
                f"feature {feature}: defaults and currencies are required"
            )
        for currency, overrides in currencies.items():
            if not isinstance(overrides, dict):
                raise QualificationError(
                    f"feature {feature}, currency {currency}: expected an object"
                )
            row = {
                **defaults,
                **overrides,
                "currency": currency,
                "feature": feature,
            }
            replacements = {
                "{CURRENCY}": str(currency),
                "{REF_AREA}": REF_AREA_BY_CURRENCY.get(str(currency), ""),
            }
            for field, value in row.items():
                if isinstance(value, str):
                    for template, replacement in replacements.items():
                        value = value.replace(template, replacement)
                    row[field] = value
            rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(str(row["decision"]) for row in rows)
    required_failures = [
        {"currency": row["currency"], "feature": row["feature"]}
        for row in rows
        if row["decision"] != "PASS"
    ]
    return {
        "row_count": len(rows),
        "currency_count": len({str(row["currency"]) for row in rows}),
        "feature_count": len({str(row["feature"]) for row in rows}),
        "decision_counts": dict(sorted(decision_counts.items())),
        "all_required_rows_pass": not required_failures,
        "phase_decision": "PASS" if not required_failures else "REVIEW_REQUIRED",
        "non_pass_rows": required_failures,
    }


def write_matrix(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
