"""Official-source downloader for the amended Phase 02 panel."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .alfred import (
    AlfredError,
    build_request,
    chunk_vintage_dates,
    fetch_observation_end,
    fetch_package,
    save_package,
)
from .research_config import ResearchConfig
from .time_utils import month_ends

EIOPA_PAGES = (
    "https://www.eiopa.europa.eu/tools-and-data/risk-free-interest-rate-"
    "term-structures/risk-free-rate-previous-releases-and-preparatory-phase_en",
    "https://www.eiopa.europa.eu/tools-and-data/"
    "risk-free-interest-rate-term-structures_en",
)
_EIOPA_BLOCK = re.compile(
    r'<div class="ecl-file".*?'
    r'<div class="ecl-file__title"[^>]*>(?P<label>.*?)</div>.*?'
    r'<a href="(?P<href>[^"]+)"[^>]*class="[^"]*ecl-file__download',
    re.DOTALL,
)
_MONTH_LABEL = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(20[0-9]{2})",
    re.IGNORECASE,
)
_MONTH_NUMBER = {
    name: index
    for index, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        start=1,
    )
}


class FetchError(RuntimeError):
    """Raised when an official-source download cannot be validated."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch(url: str, *, accept: str, retries: int = 4) -> bytes:
    request = Request(
        url,
        headers={"Accept": accept, "User-Agent": "fx-fundamental-bias-engine/0.2"},
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=180) as response:
                payload = bytes(response.read())
                if response.status != 200 or not payload:
                    raise FetchError(f"HTTP {response.status} for {url}")
                return payload
        except (HTTPError, URLError, TimeoutError, FetchError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise FetchError(f"Failed to download {url}: {last_error}")


def parse_eiopa_links(page_payloads: tuple[bytes, ...]) -> dict[str, str]:
    links: dict[str, str] = {}
    for payload in page_payloads:
        text = payload.decode("utf-8")
        for block in _EIOPA_BLOCK.finditer(text):
            label = html.unescape(re.sub(r"<[^>]+>", "", block.group("label")))
            clean_label = re.sub(r"[^A-Za-z0-9 ]", "", label)
            match = _MONTH_LABEL.search(clean_label)
            if match is None:
                continue
            month = _MONTH_NUMBER[match.group(1).lower()]
            year = int(match.group(2))
            href = html.unescape(block.group("href"))
            if ".zip" not in href.lower() and "filename=" not in href.lower():
                continue
            links[f"{year:04d}-{month:02d}"] = urljoin(EIOPA_PAGES[0], href)
    return links


def _write_snapshot(
    path: Path, *, payload: bytes, source_url: str, content_type: str
) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != payload:
            raise FetchError(f"Refusing to overwrite changed raw snapshot: {path}")
    else:
        path.write_bytes(payload)
    metadata = {
        "byte_count": len(payload),
        "content_type": content_type,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "sha256": _sha256(payload),
        "source_url": source_url,
    }
    metadata_path = path.with_suffix(path.suffix + ".metadata.json")
    if not metadata_path.exists():
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return metadata


def _ensure_download(
    path: Path, *, source_url: str, content_type: str, accept: str
) -> dict[str, object]:
    if path.exists():
        payload = path.read_bytes()
        if not payload:
            raise FetchError(f"Cached raw snapshot is empty: {path}")
        metadata_path = path.with_suffix(path.suffix + ".metadata.json")
        if metadata_path.exists():
            return dict(json.loads(metadata_path.read_text(encoding="utf-8")))
        return _write_snapshot(
            path, payload=payload, source_url=source_url, content_type=content_type
        )
    payload = _fetch(source_url, accept=accept)
    return _write_snapshot(
        path, payload=payload, source_url=source_url, content_type=content_type
    )


def _alfred_series(config: ResearchConfig) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                series.series_id
                for currency in config.currencies.values()
                for series in (
                    currency.headline,
                    currency.underlying,
                    currency.unemployment,
                )
            }
        )
    )


def fetch_phase02(config: ResearchConfig, raw_root: Path) -> dict[str, object]:
    if config.label_support_end >= config.sealed_start:
        raise FetchError("Fetch range reaches sealed data")
    raw_root.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC)

    vintages = month_ends(config.panel_start, config.panel_end)
    alfred_files: list[str] = []
    for series_id in _alfred_series(config):
        observation_end = config.panel_end
        for chunk in chunk_vintage_dates(vintages):
            request_payload = build_request(
                observation_start=date(2000, 1, 1),
                observation_end=observation_end,
                vintages=chunk,
            )
            directory = raw_root / "alfred" / series_id
            cached = tuple(
                directory.glob(f"{chunk[0]:%Y%m%d}_{chunk[-1]:%Y%m%d}_*.zip")
            )
            if len(cached) > 1:
                raise FetchError(f"Multiple cached ALFRED chunks: {series_id}/{chunk}")
            if cached:
                alfred_files.append(str(cached[0].relative_to(raw_root)))
                continue
            try:
                payload = fetch_package(series_id, request_payload)
            except AlfredError:
                advertised_end = fetch_observation_end(series_id)
                if advertised_end >= observation_end:
                    raise
                observation_end = advertised_end
                request_payload = build_request(
                    observation_start=date(2000, 1, 1),
                    observation_end=observation_end,
                    vintages=chunk,
                )
                payload = fetch_package(series_id, request_payload)
            path = save_package(
                raw_root / "alfred",
                series_id=series_id,
                request_payload=request_payload,
                payload=payload,
                vintages=chunk,
                retrieved_at=retrieved_at,
            )
            alfred_files.append(str(path.relative_to(raw_root)))

    ref_areas = "+".join(
        sorted(currency.ref_area for currency in config.currencies.values())
    )
    bis_url = (
        "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/"
        f"M.{ref_areas}?startPeriod={config.panel_start:%Y-%m}"
        f"&endPeriod={config.label_support_end:%Y-%m}"
    )
    bis_path = raw_root / "bis" / "policy_rates_monthly.csv"
    bis_metadata = _ensure_download(
        bis_path,
        source_url=bis_url,
        content_type="text/csv",
        accept="application/vnd.sdmx.data+csv;version=1.0.0",
    )

    currencies = "+".join(sorted(G10 for G10 in config.currencies if G10 != "EUR"))
    ecb_url = (
        "https://data-api.ecb.europa.eu/service/data/EXR/"
        f"D.{currencies}.EUR.SP00.A?startPeriod={config.panel_start.isoformat()}"
        f"&endPeriod={config.label_support_end.isoformat()}&format=csvdata"
    )
    ecb_path = raw_root / "ecb" / "fx_reference_daily.csv"
    ecb_metadata = _ensure_download(
        ecb_path,
        source_url=ecb_url,
        content_type="text/csv",
        accept="text/csv",
    )

    page_payloads = tuple(_fetch(url, accept="text/html") for url in EIOPA_PAGES)
    links = parse_eiopa_links(page_payloads)
    target_periods = tuple(
        value.strftime("%Y-%m")
        for value in month_ends(date(2015, 12, 1), config.label_support_end)
    )
    missing = [period for period in target_periods if period not in links]
    if missing:
        raise FetchError(f"EIOPA archive map missing periods: {missing}")
    eiopa_files: list[dict[str, object]] = []
    for period in target_periods:
        path = raw_root / "eiopa" / f"{period}.zip"
        metadata = _ensure_download(
            path,
            source_url=links[period],
            content_type="application/zip",
            accept="application/zip",
        )
        eiopa_files.append({"period": period, **metadata})

    manifest = {
        "phase": "02-canonical-panel",
        "sealed_data_accessed": False,
        "alfred_file_count": len(alfred_files),
        "alfred_files": sorted(alfred_files),
        "bis": bis_metadata,
        "ecb": ecb_metadata,
        "eiopa_file_count": len(eiopa_files),
        "eiopa": eiopa_files,
    }
    manifest_path = raw_root / "fetch_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
