"""Credential-free ALFRED vintage packages with immutable local snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ALFRED_BASE = "https://alfred.stlouisfed.org/series/downloaddata"
MAX_VINTAGE_CHARACTERS = 500
_SERIES_ID = re.compile(r"^[A-Z0-9]+$")
_VINTAGE_COLUMN = re.compile(r"^(.+)_([0-9]{8})$")
_OBSERVATION_END = re.compile(
    rb'id="form_obs_end_date"[^>]*value="([0-9]{4}-[0-9]{2}-[0-9]{2})"'
)


class AlfredError(ValueError):
    """Raised when an ALFRED payload violates the point-in-time contract."""


@dataclass(frozen=True)
class VintageTable:
    series_id: str
    vintage_dates: tuple[date, ...]
    values: dict[tuple[date, date], float]
    raw_sha256s: tuple[str, ...]

    def value(self, observation: date, vintage: date) -> float | None:
        return self.values.get((observation, vintage))

    def observation_dates(self, vintage: date) -> tuple[date, ...]:
        return tuple(
            sorted(
                observation
                for observation, item_vintage in self.values
                if item_vintage == vintage
            )
        )


def source_url(series_id: str) -> str:
    if not _SERIES_ID.fullmatch(series_id):
        raise ValueError(f"Invalid ALFRED series id: {series_id}")
    return f"{ALFRED_BASE}?seid={series_id}"


def fetch_observation_end(series_id: str, *, retries: int = 4) -> date:
    """Read the maximum observation date advertised by the ALFRED form.

    Several retired OECD series reject an otherwise valid vintage request when
    its observation end extends beyond the discontinued series.  The form is
    the authoritative, series-specific bound; using it does not reveal FX
    outcomes and does not move the requested vintage clock forward.
    """

    request = Request(
        source_url(series_id),
        headers={"Accept": "text/html", "User-Agent": "fx-fundamental-bias-engine/0.2"},
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=90) as response:
                payload = bytes(response.read())
                if response.status != 200:
                    raise AlfredError(f"ALFRED form returned HTTP {response.status}")
                match = _OBSERVATION_END.search(payload)
                if match is None:
                    raise AlfredError("ALFRED form observation-end field changed")
                return date.fromisoformat(match.group(1).decode("ascii"))
        except (HTTPError, URLError, TimeoutError, AlfredError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise AlfredError(f"Failed ALFRED form request for {series_id}: {last_error}")


def chunk_vintage_dates(
    values: tuple[date, ...], *, maximum_per_request: int = 35
) -> tuple[tuple[date, ...], ...]:
    if not values or tuple(sorted(set(values))) != values:
        raise ValueError("vintage dates must be non-empty, unique, and sorted")
    chunks: list[tuple[date, ...]] = []
    pending: list[date] = []
    for value in values:
        candidate = (*pending, value)
        encoded = " ".join(item.isoformat() for item in candidate)
        if pending and (
            len(candidate) > maximum_per_request
            or len(encoded) > MAX_VINTAGE_CHARACTERS
        ):
            chunks.append(tuple(pending))
            pending = [value]
        else:
            pending.append(value)
    if pending:
        chunks.append(tuple(pending))
    return tuple(chunks)


def build_request(
    *, observation_start: date, observation_end: date, vintages: tuple[date, ...]
) -> bytes:
    if observation_end < observation_start:
        raise ValueError("observation range is reversed")
    if not vintages or tuple(sorted(set(vintages))) != vintages:
        raise ValueError("vintages must be non-empty, unique, and sorted")
    entered = " ".join(value.isoformat() for value in vintages)
    if len(entered) > MAX_VINTAGE_CHARACTERS:
        raise ValueError("vintage request exceeds ALFRED form limit")
    fields = (
        ("form[units]", "lin"),
        ("form[obs_start_date]", observation_start.isoformat()),
        ("form[obs_end_date]", observation_end.isoformat()),
        ("form[entered_vintage_dates]", entered),
        ("form[file_type]", "2"),
        ("form[file_format]", "csv"),
        ("form[download_data]", ""),
    )
    return urlencode(fields).encode("ascii")


def fetch_package(series_id: str, request_payload: bytes, *, retries: int = 4) -> bytes:
    request = Request(
        source_url(series_id),
        data=request_payload,
        headers={
            "Accept": "application/zip",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "fx-fundamental-bias-engine/0.2",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=90) as response:
                final = urlparse(response.geturl())
                payload = bytes(response.read())
                if final.hostname != "alfred.stlouisfed.org":
                    raise AlfredError(
                        f"Unexpected ALFRED redirect: {response.geturl()}"
                    )
                if response.status != 200 or not payload.startswith(b"PK"):
                    raise AlfredError(
                        f"ALFRED did not return a ZIP for {series_id}: "
                        f"status={response.status} bytes={len(payload)}"
                    )
                return payload
        except (HTTPError, URLError, TimeoutError, AlfredError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise AlfredError(f"Failed ALFRED request for {series_id}: {last_error}")


def save_package(
    raw_root: Path,
    *,
    series_id: str,
    request_payload: bytes,
    payload: bytes,
    vintages: tuple[date, ...],
    retrieved_at: datetime,
) -> Path:
    digest = hashlib.sha256(payload).hexdigest()
    request_digest = hashlib.sha256(request_payload).hexdigest()
    directory = raw_root / series_id
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{vintages[0]:%Y%m%d}_{vintages[-1]:%Y%m%d}_{digest[:12]}"
    path = directory / f"{stem}.zip"
    metadata_path = directory / f"{stem}.metadata.json"
    if not path.exists():
        path.write_bytes(payload)
    metadata = {
        "content_type": "application/zip",
        "request_sha256": request_digest,
        "retrieved_at_utc": retrieved_at.astimezone(UTC).isoformat(),
        "series_id": series_id,
        "sha256": digest,
        "source_url": source_url(series_id),
        "vintage_dates": [value.isoformat() for value in vintages],
    }
    if not metadata_path.exists():
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return path


def parse_package(path: Path) -> VintageTable:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [
                name for name in archive.namelist() if name.lower().endswith(".csv")
            ]
            if len(members) != 1:
                raise AlfredError("ALFRED ZIP must contain exactly one CSV")
            text = archive.read(members[0]).decode("utf-8-sig")
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise AlfredError("Invalid ALFRED ZIP/CSV payload") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fields = tuple(reader.fieldnames or ())
    if not fields or fields[0] != "observation_date":
        raise AlfredError("ALFRED CSV header changed")
    series_ids: set[str] = set()
    column_dates: dict[str, date] = {}
    for field in fields[1:]:
        match = _VINTAGE_COLUMN.fullmatch(field)
        if match is None:
            raise AlfredError(f"Invalid ALFRED vintage column: {field}")
        series_ids.add(match.group(1))
        column_dates[field] = datetime.strptime(match.group(2), "%Y%m%d").date()
    if len(series_ids) != 1:
        raise AlfredError("ALFRED package has inconsistent series identifiers")
    values: dict[tuple[date, date], float] = {}
    previous: date | None = None
    for row_number, row in enumerate(reader, start=2):
        try:
            observation = date.fromisoformat(str(row["observation_date"]))
        except ValueError as exc:
            raise AlfredError(f"row {row_number}: invalid observation date") from exc
        if previous is not None and observation <= previous:
            raise AlfredError("ALFRED observations are not strictly chronological")
        previous = observation
        for field, vintage in column_dates.items():
            raw = str(row.get(field) or "").strip()
            if raw in {"", "."}:
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise AlfredError(f"row {row_number}: invalid numeric value") from exc
            if not math.isfinite(value):
                raise AlfredError(f"row {row_number}: non-finite value")
            values[(observation, vintage)] = value
    if not values:
        raise AlfredError("ALFRED package has no observations")
    return VintageTable(
        series_id=next(iter(series_ids)),
        vintage_dates=tuple(column_dates.values()),
        values=values,
        raw_sha256s=(digest,),
    )


def merge_tables(tables: tuple[VintageTable, ...]) -> VintageTable:
    if not tables:
        raise ValueError("At least one ALFRED table is required")
    series_id = tables[0].series_id
    vintages: list[date] = []
    values: dict[tuple[date, date], float] = {}
    hashes: list[str] = []
    for table in tables:
        if table.series_id != series_id:
            raise AlfredError("Cannot merge different ALFRED series")
        for key, value in table.values.items():
            if key in values and values[key] != value:
                raise AlfredError(f"Conflicting ALFRED value: {key}")
            values[key] = value
        vintages.extend(table.vintage_dates)
        hashes.extend(table.raw_sha256s)
    if len(vintages) != len(set(vintages)):
        raise AlfredError("ALFRED chunks contain overlapping vintages")
    return VintageTable(
        series_id=series_id,
        vintage_dates=tuple(sorted(vintages)),
        values=values,
        raw_sha256s=tuple(sorted(hashes)),
    )


def load_series(raw_root: Path, series_id: str) -> VintageTable:
    paths = tuple(sorted((raw_root / series_id).glob("*.zip")))
    return merge_tables(tuple(parse_package(path) for path in paths))
