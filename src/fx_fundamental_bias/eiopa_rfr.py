"""Strict reader for EIOPA risk-free-rate term-structure workbooks."""

from __future__ import annotations

import calendar
import io
import math
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_DOC_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_PACKAGE_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CELL_REFERENCE = re.compile(r"^([A-Z]+)([0-9]+)$")
_CURVE_ID = re.compile(
    r"^(?P<area>[A-Z]{2,3})_"
    r"(?:(?P<date>[0-9]{1,2}_[0-9]{1,2}_[0-9]{4})_)?"
    r"(?P<instrument>[A-Z]+)(?:_|$)"
)

type CellValue = str | float | None

G10_COUNTRY_TO_CURRENCY = {
    "Euro": "EUR",
    "Norway": "NOK",
    "Sweden": "SEK",
    "Switzerland": "CHF",
    "United Kingdom": "GBP",
    "Australia": "AUD",
    "Canada": "CAD",
    "Japan": "JPY",
    "New Zealand": "NZD",
    "United States": "USD",
}
G10_CURRENCIES = frozenset(G10_COUNTRY_TO_CURRENCY.values())


class EiopaRfrError(ValueError):
    """Raised when an EIOPA archive violates the registered parser contract."""


@dataclass(frozen=True)
class CurvePoint:
    currency: str
    country: str
    curve_id: str
    reference_date: date
    source_instrument: str
    maturity_years: int
    annual_zero_coupon_spot_decimal: float

    @property
    def rate_percent(self) -> float:
        return self.annual_zero_coupon_spot_decimal * 100.0

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["reference_date"] = self.reference_date.isoformat()
        result["rate_percent"] = self.rate_percent
        return result


def _workbook_payload(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() == ".xlsx":
        return payload
    if path.suffix.lower() != ".zip":
        raise EiopaRfrError("EIOPA input must be an outer ZIP or an XLSX workbook")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [
                name
                for name in archive.namelist()
                if "_term_structures" in name.lower()
                and name.lower().endswith(".xlsx")
            ]
            if len(members) != 1:
                raise EiopaRfrError(
                    "EIOPA archive must contain exactly one Term_Structures workbook"
                )
            return archive.read(members[0])
    except zipfile.BadZipFile as exc:
        raise EiopaRfrError("EIOPA outer archive is not a valid ZIP") from exc


def _read_xml(archive: zipfile.ZipFile, member: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(archive.read(member))
    except (KeyError, ElementTree.ParseError) as exc:
        raise EiopaRfrError(f"Invalid XLSX XML member: {member}") from exc


def _shared_strings(archive: zipfile.ZipFile) -> tuple[str, ...]:
    root = _read_xml(archive, "xl/sharedStrings.xml")
    return tuple(
        "".join(node.text or "" for node in item.iter(f"{{{_MAIN_NS}}}t"))
        for item in root.findall(f"{{{_MAIN_NS}}}si")
    )


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = _read_xml(archive, "xl/workbook.xml")
    relationship_id: str | None = None
    for sheet in workbook.findall(f".//{{{_MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{_REL_DOC_NS}}}id")
            break
    if relationship_id is None:
        raise EiopaRfrError(f"Missing EIOPA worksheet: {sheet_name}")

    relationships = _read_xml(archive, "xl/_rels/workbook.xml.rels")
    for relation in relationships.findall(f"{{{_REL_PACKAGE_NS}}}Relationship"):
        if relation.attrib.get("Id") == relationship_id:
            target = str(relation.attrib.get("Target", ""))
            if target.startswith("/"):
                target = target.lstrip("/")
            elif not target.startswith("xl/"):
                target = f"xl/{target}"
            return target
    raise EiopaRfrError(f"Missing XLSX relationship: {relationship_id}")


def _column(reference: str) -> str:
    match = _CELL_REFERENCE.fullmatch(reference)
    if match is None:
        raise EiopaRfrError(f"Invalid XLSX cell reference: {reference}")
    return match.group(1)


def _cell_value(cell: ElementTree.Element, strings: tuple[str, ...]) -> CellValue:
    kind = cell.attrib.get("t")
    value_node = cell.find(f"{{{_MAIN_NS}}}v")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{_MAIN_NS}}}t"))
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text
    if kind == "s":
        try:
            return strings[int(raw)]
        except (IndexError, ValueError) as exc:
            raise EiopaRfrError("Invalid XLSX shared-string index") from exc
    try:
        result = float(raw)
    except ValueError:
        return raw
    if not math.isfinite(result):
        raise EiopaRfrError("EIOPA workbook contains a non-finite numeric cell")
    return result


def _rows(
    archive: zipfile.ZipFile, sheet_path: str, strings: tuple[str, ...]
) -> dict[int, dict[str, CellValue]]:
    root = _read_xml(archive, sheet_path)
    result: dict[int, dict[str, CellValue]] = {}
    for row in root.findall(f".//{{{_MAIN_NS}}}row"):
        row_number = int(row.attrib["r"])
        values: dict[str, CellValue] = {}
        for cell in row.findall(f"{{{_MAIN_NS}}}c"):
            reference = str(cell.attrib.get("r", ""))
            values[_column(reference)] = _cell_value(cell, strings)
        result[row_number] = values
    return result


def parse_term_structures(
    path: Path, *, maturity_years: int = 1
) -> tuple[CurvePoint, ...]:
    """Read all G10 no-VA spot curves at one integer-year maturity."""

    if maturity_years < 1:
        raise ValueError("EIOPA workbook has no maturity below one year")
    workbook = _workbook_payload(path)
    try:
        with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
            strings = _shared_strings(archive)
            sheet_path = _sheet_path(archive, "RFR_spot_no_VA")
            rows = _rows(archive, sheet_path, strings)
    except zipfile.BadZipFile as exc:
        raise EiopaRfrError("EIOPA Term_Structures workbook is not valid XLSX") from exc

    country_row = rows.get(2, {})
    curve_row = rows.get(3, {})
    maturity_row: dict[str, CellValue] | None = None
    for candidate in rows.values():
        maturity = candidate.get("B")
        if isinstance(maturity, float) and maturity == float(maturity_years):
            maturity_row = candidate
            break
    if maturity_row is None:
        raise EiopaRfrError(f"Missing EIOPA maturity: {maturity_years} years")

    points: list[CurvePoint] = []
    for column, raw_country in country_row.items():
        if not isinstance(raw_country, str):
            continue
        currency = G10_COUNTRY_TO_CURRENCY.get(raw_country)
        if currency is None:
            continue
        raw_curve_id = curve_row.get(column)
        raw_rate = maturity_row.get(column)
        if not isinstance(raw_curve_id, str) or not isinstance(raw_rate, float):
            raise EiopaRfrError(f"Incomplete EIOPA G10 curve column: {raw_country}")
        match = _CURVE_ID.match(raw_curve_id)
        if match is None:
            raise EiopaRfrError(f"Invalid EIOPA curve identifier: {raw_curve_id}")
        raw_reference_date = match.group("date")
        if raw_reference_date is not None:
            reference_date = datetime.strptime(
                raw_reference_date, "%d_%m_%Y"
            ).date()
        else:
            archive_period = re.search(r"(20[0-9]{2})-([0-9]{2})", path.stem)
            if archive_period is None:
                raise EiopaRfrError(
                    "Curve identifier has no date and archive is undated: "
                    f"{raw_curve_id}"
                )
            year = int(archive_period.group(1))
            month = int(archive_period.group(2))
            reference_date = date(year, month, calendar.monthrange(year, month)[1])
        points.append(
            CurvePoint(
                currency=currency,
                country=raw_country,
                curve_id=raw_curve_id,
                reference_date=reference_date,
                source_instrument=match.group("instrument"),
                maturity_years=maturity_years,
                annual_zero_coupon_spot_decimal=raw_rate,
            )
        )

    found = {point.currency for point in points}
    if found != G10_CURRENCIES:
        missing = ", ".join(sorted(G10_CURRENCIES - found))
        unexpected = ", ".join(sorted(found - G10_CURRENCIES))
        raise EiopaRfrError(
            "EIOPA G10 coverage mismatch; "
            f"missing=[{missing}] unexpected=[{unexpected}]"
        )
    if len(points) != len(G10_CURRENCIES):
        raise EiopaRfrError("EIOPA workbook contains duplicate G10 curve columns")
    if len({point.reference_date for point in points}) != 1:
        raise EiopaRfrError("EIOPA G10 curves do not share one reference date")
    return tuple(sorted(points, key=lambda point: point.currency))
