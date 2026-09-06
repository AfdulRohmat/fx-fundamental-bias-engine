"""Network-free parsers and evidence builder for the Phase 01 source POC."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .eiopa_rfr import G10_CURRENCIES, CurvePoint, parse_term_structures

G10_REF_AREAS = {
    "AU": "AUD",
    "CA": "CAD",
    "CH": "CHF",
    "XM": "EUR",
    "GB": "GBP",
    "JP": "JPY",
    "NO": "NOK",
    "NZ": "NZD",
    "SE": "SEK",
    "US": "USD",
}
ECB_SAMPLE_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.USD+JPY+GBP+CHF+CAD+AUD+NZD+NOK+SEK.EUR.SP00.A?"
    "startPeriod=2024-12-01&endPeriod=2024-12-31&format=csvdata"
)
BIS_SAMPLE_URL = (
    "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/.?"
    "startPeriod=2024-12-01&endPeriod=2024-12-31"
)
EIOPA_ARCHIVE_URL = (
    "https://www.eiopa.europa.eu/tools-and-data/"
    "risk-free-interest-rate-term-structures/"
    "risk-free-rate-previous-releases-and-preparatory-phase_en"
)
EIOPA_DOWNLOAD_URLS = {
    "2018-12-31": (
        "https://www.eiopa.europa.eu/document/download/"
        "5e47b36b-f322-4239-a680-ef5a0a8cc745_en?filename=December+2018.zip"
    ),
    "2024-12-31": (
        "https://www.eiopa.europa.eu/document/download/"
        "946ea3f4-881b-405b-ae54-e1b930901527_en?"
        "filename=EIOPA_RFR_20241231.zip"
    ),
}


class SourcePocError(ValueError):
    """Raised when a source POC payload violates the registered contract."""


@dataclass(frozen=True)
class AlfredEvidence:
    series_id: str
    vintage_dates: tuple[date, ...]
    observation_count: int
    first_observation: date
    last_observation: date
    comparable_cell_count: int
    changed_cell_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "series_id": self.series_id,
            "vintage_dates": [item.isoformat() for item in self.vintage_dates],
            "observation_count": self.observation_count,
            "first_observation": self.first_observation.isoformat(),
            "last_observation": self.last_observation.isoformat(),
            "comparable_cell_count": self.comparable_cell_count,
            "changed_cell_count": self.changed_cell_count,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retrieved_at_utc(path: Path) -> str:
    return (
        datetime.fromtimestamp(path.stat().st_mtime, UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _csv_rows(payload: bytes) -> list[dict[str, str]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourcePocError("Source CSV is not UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise SourcePocError("Source CSV has no header")
    return [dict(row) for row in reader]


def audit_ecb_fx(path: Path) -> dict[str, object]:
    rows = _csv_rows(path.read_bytes())
    required = {"CURRENCY", "CURRENCY_DENOM", "TIME_PERIOD", "OBS_VALUE"}
    if not rows or not required.issubset(rows[0]):
        raise SourcePocError("ECB CSV header changed")
    expected = G10_CURRENCIES - {"EUR"}
    dates_by_currency: dict[str, set[str]] = {}
    values: dict[tuple[str, str], float] = {}
    for row in rows:
        currency = row["CURRENCY"]
        if currency not in expected:
            raise SourcePocError(f"Unexpected ECB currency: {currency}")
        if row["CURRENCY_DENOM"] != "EUR":
            raise SourcePocError("ECB source leg is not currency per EUR")
        try:
            value = float(row["OBS_VALUE"])
            date.fromisoformat(row["TIME_PERIOD"])
        except ValueError as exc:
            raise SourcePocError("Invalid ECB FX observation") from exc
        if not math.isfinite(value) or value <= 0:
            raise SourcePocError("ECB FX rate must be finite and positive")
        key = (currency, row["TIME_PERIOD"])
        if key in values:
            raise SourcePocError(f"Duplicate ECB FX observation: {key}")
        values[key] = value
        dates_by_currency.setdefault(currency, set()).add(row["TIME_PERIOD"])
    if set(dates_by_currency) != expected:
        raise SourcePocError("ECB FX sample does not contain all nine non-EUR legs")
    common_dates = set.intersection(*dates_by_currency.values())
    if not common_dates:
        raise SourcePocError("ECB FX legs have no common observation date")
    example_date = max(common_dates)
    usd_jpy = values[("JPY", example_date)] / values[("USD", example_date)]
    return {
        "status": "PASS",
        "source_url": ECB_SAMPLE_URL,
        "content_type": "text/csv",
        "retrieved_at_utc": retrieved_at_utc(path),
        "source_sha256": sha256_file(path),
        "currencies": sorted(dates_by_currency),
        "rows_per_currency": {
            currency: len(dates_by_currency[currency])
            for currency in sorted(dates_by_currency)
        },
        "common_date_count": len(common_dates),
        "cross_example": {
            "pair": "USDJPY",
            "date": example_date,
            "formula": "JPY_per_EUR / USD_per_EUR",
            "rate": usd_jpy,
        },
        "limitation": "Indicative ECB reference marks, not executable quotes.",
    }


def audit_bis_policy_rates(path: Path) -> dict[str, object]:
    rows = _csv_rows(path.read_bytes())
    required = {"FREQ", "REF_AREA", "TIME_PERIOD", "OBS_VALUE", "COMPILATION"}
    if not rows or not required.issubset(rows[0]):
        raise SourcePocError("BIS policy-rate CSV header changed")
    observations: dict[str, list[tuple[str, float]]] = {
        currency: [] for currency in G10_REF_AREAS.values()
    }
    compilation: dict[str, str] = {}
    for row in rows:
        currency = G10_REF_AREAS.get(row["REF_AREA"])
        if currency is None or row["FREQ"] != "D":
            continue
        try:
            value = float(row["OBS_VALUE"])
            date.fromisoformat(row["TIME_PERIOD"])
        except ValueError:
            continue
        if not math.isfinite(value):
            continue
        observations[currency].append((row["TIME_PERIOD"], value))
        compilation[currency] = row["COMPILATION"]
    missing = [currency for currency, values in observations.items() if not values]
    if missing:
        raise SourcePocError(f"BIS policy-rate sample missing: {', '.join(missing)}")
    latest = {
        currency: {"date": max(values)[0], "rate_percent": max(values)[1]}
        for currency, values in sorted(observations.items())
    }
    return {
        "status": "PASS_FOR_SCALAR_HISTORY",
        "source_url": BIS_SAMPLE_URL,
        "content_type": "text/csv",
        "retrieved_at_utc": retrieved_at_utc(path),
        "source_sha256": sha256_file(path),
        "currencies": sorted(observations),
        "latest": latest,
        "compilation": dict(sorted(compilation.items())),
        "limitation": (
            "Effective-rate series; exact decision announcement timestamps and "
            "historical corridor conventions still require bank profiles."
        ),
    }


def audit_alfred_vintages(path: Path) -> AlfredEvidence:
    try:
        with zipfile.ZipFile(path) as archive:
            csv_members = [
                name for name in archive.namelist() if name.lower().endswith(".csv")
            ]
            if len(csv_members) != 1:
                raise SourcePocError("ALFRED ZIP must contain exactly one CSV")
            rows = _csv_rows(archive.read(csv_members[0]))
    except zipfile.BadZipFile as exc:
        raise SourcePocError("ALFRED payload is not a valid ZIP") from exc
    if not rows or "observation_date" not in rows[0]:
        raise SourcePocError("ALFRED vintage CSV header changed")
    columns = [column for column in rows[0] if column != "observation_date"]
    if len(columns) < 2:
        raise SourcePocError("ALFRED POC requires at least two vintage columns")
    series_ids: set[str] = set()
    vintage_dates: list[date] = []
    for column in columns:
        try:
            series_id, raw_date = column.rsplit("_", 1)
            vintage_dates.append(datetime.strptime(raw_date, "%Y%m%d").date())
            series_ids.add(series_id)
        except ValueError as exc:
            raise SourcePocError(f"Invalid ALFRED vintage column: {column}") from exc
    if len(series_ids) != 1:
        raise SourcePocError("ALFRED vintage columns contain different series")
    comparable = 0
    changed = 0
    observation_dates: list[date] = []
    for row in rows:
        try:
            observation_dates.append(date.fromisoformat(row["observation_date"]))
        except ValueError as exc:
            raise SourcePocError("Invalid ALFRED observation date") from exc
        values = [row[column].strip() for column in columns]
        if all(value not in {"", "."} for value in values):
            parsed = [float(value) for value in values]
            comparable += 1
            if len(set(parsed)) > 1:
                changed += 1
    return AlfredEvidence(
        series_id=next(iter(series_ids)),
        vintage_dates=tuple(vintage_dates),
        observation_count=len(rows),
        first_observation=min(observation_dates),
        last_observation=max(observation_dates),
        comparable_cell_count=comparable,
        changed_cell_count=changed,
    )


def _eiopa_evidence(path: Path) -> dict[str, object]:
    points: tuple[CurvePoint, ...] = parse_term_structures(path)
    reference_date = points[0].reference_date.isoformat()
    return {
        "path_name": path.name,
        "source_page_url": EIOPA_ARCHIVE_URL,
        "source_url": EIOPA_DOWNLOAD_URLS.get(reference_date, EIOPA_ARCHIVE_URL),
        "content_type": "application/zip",
        "retrieved_at_utc": retrieved_at_utc(path),
        "source_sha256": sha256_file(path),
        "reference_date": reference_date,
        "maturity_years": points[0].maturity_years,
        "currencies": [point.currency for point in points],
        "source_instruments": sorted({point.source_instrument for point in points}),
        "source_instrument_by_currency": {
            point.currency: point.source_instrument for point in points
        },
        "rates_percent": {point.currency: point.rate_percent for point in points},
    }


def build_phase01_evidence(
    *,
    eiopa_paths: Iterable[Path],
    ecb_path: Path,
    bis_path: Path,
    alfred_paths: Iterable[Path],
) -> dict[str, Any]:
    eiopa = [_eiopa_evidence(path) for path in eiopa_paths]
    if len(eiopa) < 2:
        raise SourcePocError("EIOPA POC requires at least two archive dates")
    alfred = []
    seen_series: set[str] = set()
    for path in alfred_paths:
        series_id = path.stem
        if series_id in seen_series:
            raise SourcePocError(f"Duplicate ALFRED series: {series_id}")
        seen_series.add(series_id)
        try:
            audit = audit_alfred_vintages(path)
            if audit.series_id != series_id:
                raise SourcePocError(
                    f"ALFRED filename/series mismatch: {series_id}/{audit.series_id}"
                )
            alfred.append(
                {
                    **audit.as_dict(),
                    "source_url": (
                        "https://alfred.stlouisfed.org/series/downloaddata?"
                        f"seid={series_id}"
                    ),
                    "content_type": "application/zip",
                    "retrieved_at_utc": retrieved_at_utc(path),
                    "source_sha256": sha256_file(path),
                    "status": "PASS_FOR_REQUESTED_VINTAGES",
                }
            )
        except SourcePocError as exc:
            payload = path.read_bytes()
            text = payload.decode("utf-8", errors="ignore")
            selectable = sorted(
                set(
                    re.findall(
                        r'<option value="([0-9]{4}-[0-9]{2}-[0-9]{2})"',
                        text,
                    )
                )
            )
            alfred.append(
                {
                    "series_id": series_id,
                    "source_url": (
                        "https://alfred.stlouisfed.org/series/downloaddata?"
                        f"seid={series_id}"
                    ),
                    "content_type": "text/html",
                    "retrieved_at_utc": retrieved_at_utc(path),
                    "source_sha256": sha256_file(path),
                    "status": "FAIL_REQUEST_RETURNED_HTML",
                    "reason": str(exc),
                    "last_selectable_vintage": selectable[-1] if selectable else None,
                }
            )
    if not alfred:
        raise SourcePocError("ALFRED POC requires at least one vintage package")
    return {
        "phase": "01-source-qualification",
        "outcome_data_read": False,
        "pocs": {
            "alfred_macro_vintage": {
                "status": (
                    "PASS_FOR_ALL_REQUESTED_VINTAGES"
                    if all(
                        item["status"] == "PASS_FOR_REQUESTED_VINTAGES"
                        for item in alfred
                    )
                    else "REVIEW_REQUIRED"
                ),
                "series_count": len(alfred),
                "series_pass_count": sum(
                    item["status"] == "PASS_FOR_REQUESTED_VINTAGES" for item in alfred
                ),
                "series_fail_count": sum(
                    item["status"] != "PASS_FOR_REQUESTED_VINTAGES" for item in alfred
                ),
                "series": sorted(alfred, key=lambda item: str(item["series_id"])),
                "limitation": (
                    "Vintage-date columns are available, but exact intraday release "
                    "times and bank-specific indicator suitability still need profiles."
                ),
            },
            "bis_policy_rate": audit_bis_policy_rates(bis_path),
            "ecb_fx": audit_ecb_fx(ecb_path),
            "eiopa_rfr_proxy": {
                "status": "PASS_AS_SECONDARY_1Y_PROXY_ONLY",
                "samples": eiopa,
                "limitation": (
                    "Annual zero-coupon risk-free curve with minimum one-year "
                    "tenor; not a six-month OIS-implied policy path."
                ),
            },
        },
        "primary_expectation_gate": {
            "status": "FAIL",
            "reason": (
                "No free, point-in-time, six-month Tier A policy-expectation "
                "history has been qualified for every G10 currency."
            ),
        },
        "phase_decision": "REVIEW_REQUIRED",
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8", newline="\n")
